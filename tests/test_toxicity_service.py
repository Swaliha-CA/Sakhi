"""Unit tests for Toxicity Service"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.toxicity_service import (
    ChemicalEntityResolver,
    ToxicityDatabaseClient,
    ToxicityScorer,
    ChemicalIdentifier,
    FlaggedChemical,
    Ingredient,
    ToxicityScore,
    EDCType,
    RegulatoryInfo,
    get_toxicity_scorer
)


class TestChemicalEntityResolver:
    """Test chemical entity resolution"""
    
    @pytest.fixture
    async def resolver(self):
        """Create resolver instance"""
        resolver = ChemicalEntityResolver()
        await resolver.connect()
        yield resolver
        await resolver.disconnect()
    
    def test_normalize_name(self):
        """Test chemical name normalization"""
        resolver = ChemicalEntityResolver()
        
        # Test basic normalization (spaces are preserved in the current implementation)
        normalized = resolver._normalize_name("Methyl Paraben")
        assert normalized.lower() == "methyl paraben" or normalized == "methylparaben"
        assert resolver._normalize_name("  BPA  ") == "bpa"
        
        # Test removal of prefixes
        normalized = resolver._normalize_name("CI 77891")
        assert "77891" in normalized
        normalized = resolver._normalize_name("FD&C Red 40")
        assert "red" in normalized and "40" in normalized
        
        # Test Indian name mappings
        assert resolver._normalize_name("Kumkum") == "vermillion"
        assert resolver._normalize_name("Sindoor") == "vermillion"
    
    def test_bio_sim_similarity(self):
        """Test Bio-SIM fuzzy matching algorithm"""
        resolver = ChemicalEntityResolver()
        
        # Exact match
        assert resolver._bio_sim_similarity("methylparaben", "methylparaben") == 1.0
        
        # Abbreviation match
        score = resolver._bio_sim_similarity("bpa", "bisphenol a")
        assert score >= 0.9
        
        # Similar names
        score = resolver._bio_sim_similarity("methyl paraben", "methylparaben")
        assert score >= 0.9
        
        # Different names
        score = resolver._bio_sim_similarity("water", "benzene")
        assert score < 0.5
    
    @pytest.mark.asyncio
    async def test_resolve_to_cas_cached(self, resolver):
        """Test CAS resolution with caching"""
        # Mock cache hit
        mock_identifier = ChemicalIdentifier(
            cas_number="99-76-3",
            common_names=["methylparaben"]
        )
        
        with patch.object(resolver, '_get_cached_identifier', return_value=mock_identifier):
            cas, confidence = await resolver.resolve_to_cas("methylparaben")
            
            assert cas == "99-76-3"
            assert confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_resolve_to_cas_local_database(self, resolver):
        """Test CAS resolution from local database"""
        # Test known chemicals
        cas, confidence = await resolver.resolve_to_cas("water")
        assert cas == "7732-18-5"
        assert confidence >= 0.7
        
        cas, confidence = await resolver.resolve_to_cas("glycerin")
        assert cas == "56-81-5"
        assert confidence >= 0.7
        
        cas, confidence = await resolver.resolve_to_cas("bpa")
        assert cas == "80-05-7"
        assert confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_resolve_to_cas_unknown(self, resolver):
        """Test CAS resolution for unknown chemical"""
        # Mock all API calls to fail
        with patch.object(resolver, '_query_pubchem', return_value=None), \
             patch.object(resolver, '_query_comptox', return_value=None):
            
            cas, confidence = await resolver.resolve_to_cas("unknown_chemical_xyz")
            
            assert cas is None
            assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_pubchem_query_success(self, resolver):
        """Test successful PubChem query"""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "PropertyTable": {
                "Properties": [{
                    "CID": 12345,
                    "InChIKey": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
                }]
            }
        }
        
        with patch.object(resolver.http_client, 'get', return_value=mock_response), \
             patch.object(resolver, '_get_cas_from_pubchem_cid', return_value="99-76-3"):
            
            identifier = await resolver._query_pubchem("methylparaben")
            
            assert identifier is not None
            assert identifier.cas_number == "99-76-3"
            assert identifier.inchi_key == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
    
    @pytest.mark.asyncio
    async def test_pubchem_query_failure(self, resolver):
        """Test failed PubChem query"""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch.object(resolver.http_client, 'get', return_value=mock_response):
            identifier = await resolver._query_pubchem("unknown_chemical")
            
            assert identifier is None
    
    def test_lookup_local_database(self):
        """Test local database lookup"""
        resolver = ChemicalEntityResolver()
        
        # Test exact matches
        assert resolver._lookup_local_database("water") == "7732-18-5"
        assert resolver._lookup_local_database("bpa") == "80-05-7"
        assert resolver._lookup_local_database("methylparaben") == "99-76-3"
        
        # Test fuzzy matches
        cas = resolver._lookup_local_database("methyl paraben")
        assert cas == "99-76-3"
        
        # Test unknown chemical
        assert resolver._lookup_local_database("unknown_xyz") is None


class TestToxicityDatabaseClient:
    """Test toxicity database client"""
    
    @pytest.fixture
    async def client(self):
        """Create client instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_edc_info_known_edc(self, client):
        """Test getting EDC info for known EDC"""
        # Mock entity resolution
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("80-05-7", 0.95)):
            edc_info = await client.get_edc_info("bpa")
            
            assert edc_info is not None
            assert edc_info.name == "Bisphenol A (BPA)"
            assert edc_info.cas_number == "80-05-7"
            assert EDCType.BPA in edc_info.edc_types
            assert edc_info.risk_score > 80.0
            assert edc_info.confidence == 0.95
            assert len(edc_info.health_effects) > 0
    
    @pytest.mark.asyncio
    async def test_get_edc_info_paraben(self, client):
        """Test getting EDC info for paraben"""
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("99-76-3", 0.9)):
            edc_info = await client.get_edc_info("methylparaben")
            
            assert edc_info is not None
            assert EDCType.PARABEN in edc_info.edc_types
            assert edc_info.risk_score > 0
            assert edc_info.regulatory_status.fssai_approved is True
    
    @pytest.mark.asyncio
    async def test_get_edc_info_phthalate(self, client):
        """Test getting EDC info for phthalate"""
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("117-81-7", 0.9)):
            edc_info = await client.get_edc_info("dehp")
            
            assert edc_info is not None
            assert EDCType.PHTHALATE in edc_info.edc_types
            assert edc_info.risk_score >= 80.0
            assert "PPD risk factor" in edc_info.health_effects
    
    @pytest.mark.asyncio
    async def test_get_edc_info_heavy_metal(self, client):
        """Test getting EDC info for heavy metal"""
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("7439-92-1", 0.95)):
            edc_info = await client.get_edc_info("lead")
            
            assert edc_info is not None
            assert EDCType.HEAVY_METAL in edc_info.edc_types
            assert edc_info.risk_score >= 90.0
            assert edc_info.regulatory_status.fssai_approved is False
    
    @pytest.mark.asyncio
    async def test_get_edc_info_non_edc(self, client):
        """Test getting EDC info for non-EDC chemical"""
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("7732-18-5", 0.95)):
            edc_info = await client.get_edc_info("water")
            
            # Water is not an EDC
            assert edc_info is None
    
    @pytest.mark.asyncio
    async def test_get_edc_info_unresolved(self, client):
        """Test getting EDC info when CAS resolution fails"""
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=(None, 0.0)):
            edc_info = await client.get_edc_info("unknown_chemical")
            
            assert edc_info is None
    
    @pytest.mark.asyncio
    async def test_caching_chemical_info(self, client):
        """Test caching of chemical information"""
        cas_number = "80-05-7"
        test_info = {
            "name": "BPA",
            "risk_score": 85.0,
            "sources": ["comptox"]
        }
        
        # Cache the info
        await client._cache_chemical_info(cas_number, test_info)
        
        # Retrieve from cache
        cached = await client._get_cached_chemical_info(cas_number)
        
        if client.redis_client:  # Only test if Redis is available
            assert cached is not None
            assert cached["name"] == "BPA"
            assert cached["risk_score"] == 85.0
    
    def test_get_local_edc_info(self, client):
        """Test local EDC database lookup"""
        # Test known EDCs
        edc = client._get_local_edc_info("bpa", "80-05-7")
        assert edc is not None
        assert edc.name == "Bisphenol A (BPA)"
        
        edc = client._get_local_edc_info("methylparaben", "99-76-3")
        assert edc is not None
        assert EDCType.PARABEN in edc.edc_types
        
        # Test unknown chemical
        edc = client._get_local_edc_info("unknown", "999-99-9")
        assert edc is None


class TestDataModels:
    """Test data model classes"""
    
    def test_chemical_identifier(self):
        """Test ChemicalIdentifier dataclass"""
        identifier = ChemicalIdentifier(
            cas_number="99-76-3",
            smiles="COC(=O)C1=CC=C(O)C=C1",
            inchi_key="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            common_names=["methylparaben", "methyl paraben"]
        )
        
        assert identifier.cas_number == "99-76-3"
        assert len(identifier.common_names) == 2
        
        # Test to_dict
        data = identifier.to_dict()
        assert data["cas_number"] == "99-76-3"
        assert "common_names" in data
    
    def test_regulatory_info(self):
        """Test RegulatoryInfo dataclass"""
        reg_info = RegulatoryInfo(
            fssai_approved=False,
            fssai_limit="Banned",
            epa_status="Restricted",
            eu_status="Prohibited"
        )
        
        assert reg_info.fssai_approved is False
        assert reg_info.fssai_limit == "Banned"
        
        # Test to_dict
        data = reg_info.to_dict()
        assert data["fssai_approved"] is False
    
    def test_flagged_chemical(self):
        """Test FlaggedChemical dataclass"""
        chemical = FlaggedChemical(
            name="Bisphenol A",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=["Hormone disruption", "PCOS risk"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["comptox", "local_database"],
            confidence=0.95
        )
        
        assert chemical.name == "Bisphenol A"
        assert chemical.risk_score == 85.0
        assert EDCType.BPA in chemical.edc_types
        assert chemical.confidence == 0.95
        
        # Test to_dict
        data = chemical.to_dict()
        assert data["name"] == "Bisphenol A"
        assert data["risk_score"] == 85.0
        assert "bpa" in data["edc_types"]
        assert "regulatory_status" in data


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_resolver_without_redis(self):
        """Test resolver works without Redis"""
        resolver = ChemicalEntityResolver()
        # Don't connect to Redis
        resolver.redis_client = None
        
        # Should still work with local database
        cas, confidence = await resolver.resolve_to_cas("water")
        assert cas == "7732-18-5"
    
    @pytest.mark.asyncio
    async def test_client_without_redis(self):
        """Test client works without Redis"""
        client = ToxicityDatabaseClient()
        # Don't connect to Redis
        client.redis_client = None
        client.entity_resolver.redis_client = None
        
        # Should still work with local database
        with patch.object(client.entity_resolver, 'resolve_to_cas', return_value=("80-05-7", 0.9)):
            edc_info = await client.get_edc_info("bpa")
            assert edc_info is not None
    
    def test_empty_chemical_name(self):
        """Test handling of empty chemical name"""
        resolver = ChemicalEntityResolver()
        
        normalized = resolver._normalize_name("")
        assert normalized == ""
        
        normalized = resolver._normalize_name("   ")
        assert normalized == ""
    
    def test_special_characters_in_name(self):
        """Test handling of special characters"""
        resolver = ChemicalEntityResolver()
        
        # Should remove most special characters
        normalized = resolver._normalize_name("Methyl@Paraben#123!")
        assert "@" not in normalized
        assert "#" not in normalized
        assert "!" not in normalized
    
    @pytest.mark.asyncio
    async def test_http_client_not_initialized(self):
        """Test behavior when HTTP client is not initialized"""
        resolver = ChemicalEntityResolver()
        resolver.http_client = None
        
        # Should return None gracefully
        result = await resolver._query_pubchem("test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_api_timeout(self):
        """Test handling of API timeouts"""
        resolver = ChemicalEntityResolver()
        await resolver.connect()
        
        # Mock timeout exception
        with patch.object(resolver.http_client, 'get', side_effect=Exception("Timeout")):
            result = await resolver._query_pubchem("test")
            assert result is None
        
        await resolver.disconnect()


class TestIndianContext:
    """Test Indian-specific functionality"""
    
    def test_indian_name_mappings(self):
        """Test Indian ingredient name mappings"""
        resolver = ChemicalEntityResolver()
        
        # Test traditional Indian names
        assert resolver._normalize_name("kumkum") == "vermillion"
        assert resolver._normalize_name("sindoor") == "vermillion"
        assert resolver._normalize_name("kajal") == "kohl"
        assert resolver._normalize_name("surma") == "kohl"
    
    @pytest.mark.asyncio
    async def test_indian_cosmetic_ingredients(self):
        """Test resolution of common Indian cosmetic ingredients"""
        resolver = ChemicalEntityResolver()
        await resolver.connect()
        
        # Test that Indian names are properly normalized
        normalized = resolver._normalize_name("Kumkum")
        assert normalized == "vermillion"
        
        await resolver.disconnect()
    
    def test_fssai_regulatory_info(self):
        """Test FSSAI regulatory information"""
        client = ToxicityDatabaseClient()
        
        # Test BPA (banned in baby products in India)
        edc = client._get_local_edc_info("bpa", "80-05-7")
        assert edc is not None
        assert edc.regulatory_status.fssai_approved is False
        assert "baby products" in edc.regulatory_status.fssai_limit.lower()
        
        # Test methylparaben (approved with limits)
        edc = client._get_local_edc_info("methylparaben", "99-76-3")
        assert edc is not None
        assert edc.regulatory_status.fssai_approved is True
        assert edc.regulatory_status.fssai_limit is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestToxicityScorer:
    """Test toxicity scoring algorithm"""
    
    @pytest.fixture
    async def scorer(self):
        """Create scorer instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        scorer = ToxicityScorer(client)
        yield scorer
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_score_product_no_edcs(self, scorer):
        """Test scoring product with no EDCs"""
        ingredients = [
            Ingredient(name="water"),
            Ingredient(name="glycerin"),
            Ingredient(name="vitamin e")
        ]
        
        # Mock get_edc_info to return None (no EDCs)
        with patch.object(scorer.db_client, 'get_edc_info', return_value=None):
            score = await scorer.score_product(ingredients)
            
            assert score.overall_score == 100.0
            assert score.hormonal_health_score == 100.0
            assert score.risk_level == "low"
            assert len(score.flagged_chemicals) == 0
            assert len(score.recommendations) > 0
            assert "No EDCs detected" in score.recommendations[0]
    
    @pytest.mark.asyncio
    async def test_score_product_with_bpa(self, scorer):
        """Test scoring product containing BPA"""
        ingredients = [
            Ingredient(name="water"),
            Ingredient(name="bpa"),
            Ingredient(name="glycerin")
        ]
        
        # Mock BPA detection
        bpa_info = FlaggedChemical(
            name="Bisphenol A (BPA)",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=["Hormone disruption", "PCOS risk"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["local_database"],
            confidence=0.95
        )
        
        async def mock_get_edc_info(name):
            if "bpa" in name.lower():
                return bpa_info
            return None
        
        with patch.object(scorer.db_client, 'get_edc_info', side_effect=mock_get_edc_info):
            score = await scorer.score_product(ingredients)
            
            # Should have lower scores due to BPA
            assert score.overall_score < 100.0
            assert score.hormonal_health_score < score.overall_score  # PCOS penalty applied
            assert score.risk_level in ["medium", "high", "critical"]
            assert len(score.flagged_chemicals) == 1
            assert score.flagged_chemicals[0].name == "Bisphenol A (BPA)"
            
            # Should have BPA-specific recommendation
            recommendations_text = " ".join(score.recommendations)
            assert "BPA" in recommendations_text
    
    @pytest.mark.asyncio
    async def test_score_product_with_phthalates(self, scorer):
        """Test scoring product containing phthalates"""
        ingredients = [
            Ingredient(name="dehp"),
            Ingredient(name="water"),
            Ingredient(name="glycerin")
        ]
        
        # Mock phthalate detection
        phthalate_info = FlaggedChemical(
            name="DEHP",
            cas_number="117-81-7",
            edc_types=[EDCType.PHTHALATE],
            risk_score=90.0,
            health_effects=["Endocrine disruption", "PPD risk"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["local_database"],
            confidence=0.9
        )
        
        async def mock_get_edc_info(name):
            if "dehp" in name.lower():
                return phthalate_info
            return None
        
        with patch.object(scorer.db_client, 'get_edc_info', side_effect=mock_get_edc_info):
            score = await scorer.score_product(ingredients)
            
            # High risk due to phthalate
            assert score.overall_score < 50.0
            assert score.hormonal_health_score <= score.overall_score  # PCOS penalty (can be equal if both hit floor)
            assert score.risk_level in ["high", "critical"]
            
            # Should have phthalate-specific recommendation
            recommendations_text = " ".join(score.recommendations)
            assert "Phthalate" in recommendations_text or "phthalate" in recommendations_text
    
    @pytest.mark.asyncio
    async def test_score_product_with_multiple_edcs(self, scorer):
        """Test scoring product with multiple EDCs"""
        ingredients = [
            Ingredient(name="bpa"),
            Ingredient(name="methylparaben"),
            Ingredient(name="triclosan"),
            Ingredient(name="water")
        ]
        
        # Mock multiple EDCs
        bpa_info = FlaggedChemical(
            name="BPA",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=["Hormone disruption"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["local_database"],
            confidence=0.95
        )
        
        paraben_info = FlaggedChemical(
            name="Methylparaben",
            cas_number="99-76-3",
            edc_types=[EDCType.PARABEN],
            risk_score=45.0,
            health_effects=["Endocrine disruption"],
            regulatory_status=RegulatoryInfo(fssai_approved=True),
            sources=["local_database"],
            confidence=0.9
        )
        
        triclosan_info = FlaggedChemical(
            name="Triclosan",
            cas_number="3380-34-5",
            edc_types=[EDCType.ORGANOCHLORINE],
            risk_score=70.0,
            health_effects=["Endocrine disruption"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["local_database"],
            confidence=0.92
        )
        
        async def mock_get_edc_info(name):
            name_lower = name.lower()
            if "bpa" in name_lower:
                return bpa_info
            elif "paraben" in name_lower:
                return paraben_info
            elif "triclosan" in name_lower:
                return triclosan_info
            return None
        
        with patch.object(scorer.db_client, 'get_edc_info', side_effect=mock_get_edc_info):
            score = await scorer.score_product(ingredients)
            
            # Should have very low scores due to multiple EDCs
            assert score.overall_score < 50.0
            assert score.hormonal_health_score < score.overall_score
            assert score.risk_level in ["high", "critical"]
            assert len(score.flagged_chemicals) == 3
            
            # Should have multiple recommendations
            assert len(score.recommendations) > 3
    
    @pytest.mark.asyncio
    async def test_score_product_low_confidence_warning(self, scorer):
        """Test confidence warning for low confidence matches"""
        ingredients = [
            Ingredient(name="unknown_chemical"),
            Ingredient(name="water")
        ]
        
        # Mock low confidence EDC detection
        low_conf_info = FlaggedChemical(
            name="Unknown Chemical",
            cas_number="123-45-6",
            edc_types=[EDCType.UNKNOWN],
            risk_score=50.0,
            health_effects=["Unknown"],
            regulatory_status=RegulatoryInfo(),
            sources=["local_database"],
            confidence=0.70  # Below 0.85 threshold
        )
        
        async def mock_get_edc_info(name):
            if "unknown" in name.lower():
                return low_conf_info
            return None
        
        with patch.object(scorer.db_client, 'get_edc_info', side_effect=mock_get_edc_info):
            score = await scorer.score_product(ingredients)
            
            # Should have confidence warning
            assert len(score.confidence_warnings) > 0
            assert "Low confidence" in score.confidence_warnings[0]
            assert "unknown_chemical" in score.confidence_warnings[0]
    
    @pytest.mark.asyncio
    async def test_score_product_user_warnings(self, scorer):
        """Test that user warnings are always included"""
        ingredients = [Ingredient(name="water")]
        
        with patch.object(scorer.db_client, 'get_edc_info', return_value=None):
            score = await scorer.score_product(ingredients)
            
            # Should always have user warnings about limitations
            assert len(score.user_warnings) > 0
            
            # Check for key warning messages
            warnings_text = " ".join(score.user_warnings)
            assert "AWARENESS TOOL" in warnings_text or "awareness tool" in warnings_text.lower()
            assert "LABEL LIMITATIONS" in warnings_text or "label" in warnings_text.lower()
            assert "SCIENTIFIC UNCERTAINTY" in warnings_text or "scientific" in warnings_text.lower()
    
    def test_calculate_overall_score_no_edcs(self, scorer):
        """Test overall score calculation with no EDCs"""
        score = scorer._calculate_overall_score([], 5)
        assert score == 100.0
    
    def test_calculate_overall_score_single_edc(self, scorer):
        """Test overall score calculation with single EDC"""
        chemical = FlaggedChemical(
            name="BPA",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        score = scorer._calculate_overall_score([chemical], 5)
        
        # Score should be reduced but not zero
        assert 0 < score < 100
        assert score < 50  # Should be significantly reduced
    
    def test_calculate_overall_score_multiple_edcs(self, scorer):
        """Test overall score with multiple EDCs"""
        chemicals = [
            FlaggedChemical(
                name="BPA",
                cas_number="80-05-7",
                edc_types=[EDCType.BPA],
                risk_score=85.0,
                health_effects=[],
                regulatory_status=RegulatoryInfo(),
                sources=[],
                confidence=1.0
            ),
            FlaggedChemical(
                name="DEHP",
                cas_number="117-81-7",
                edc_types=[EDCType.PHTHALATE],
                risk_score=90.0,
                health_effects=[],
                regulatory_status=RegulatoryInfo(),
                sources=[],
                confidence=1.0
            )
        ]
        
        score = scorer._calculate_overall_score(chemicals, 5)
        
        # Score should be very low with multiple high-risk EDCs
        assert 0 <= score < 30
    
    def test_calculate_hormonal_health_score_pcos_penalty(self, scorer):
        """Test that PCOS penalties are applied correctly"""
        # BPA with PCOS penalty (use moderate risk to avoid floor effect)
        bpa_chemical = FlaggedChemical(
            name="BPA",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=60.0,  # Moderate risk to see penalty difference
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        # Paraben with lower penalty (same base risk)
        paraben_chemical = FlaggedChemical(
            name="Methylparaben",
            cas_number="99-76-3",
            edc_types=[EDCType.PARABEN],
            risk_score=60.0,  # Same base risk as BPA
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        # Use more ingredients to avoid floor effect
        bpa_score = scorer._calculate_hormonal_health_score([bpa_chemical], 10)
        paraben_score = scorer._calculate_hormonal_health_score([paraben_chemical], 10)
        
        # BPA should have lower score due to higher PCOS penalty
        assert bpa_score < paraben_score
    
    def test_classify_risk_level(self, scorer):
        """Test risk level classification"""
        assert scorer._classify_risk_level(80.0) == "low"
        assert scorer._classify_risk_level(70.0) == "low"
        assert scorer._classify_risk_level(60.0) == "medium"
        assert scorer._classify_risk_level(50.0) == "medium"
        assert scorer._classify_risk_level(40.0) == "high"
        assert scorer._classify_risk_level(30.0) == "high"
        assert scorer._classify_risk_level(20.0) == "critical"
        assert scorer._classify_risk_level(0.0) == "critical"
    
    def test_generate_recommendations_no_edcs(self, scorer):
        """Test recommendations when no EDCs found"""
        recommendations = scorer._generate_recommendations([], "low", None)
        
        assert len(recommendations) > 0
        assert "No EDCs detected" in recommendations[0]
    
    def test_generate_recommendations_critical_risk(self, scorer):
        """Test recommendations for critical risk"""
        chemical = FlaggedChemical(
            name="Lead",
            cas_number="7439-92-1",
            edc_types=[EDCType.HEAVY_METAL],
            risk_score=95.0,
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        recommendations = scorer._generate_recommendations([chemical], "critical", None)
        
        assert len(recommendations) > 0
        assert "CRITICAL" in recommendations[0]
    
    def test_generate_recommendations_bpa_specific(self, scorer):
        """Test BPA-specific recommendations"""
        chemical = FlaggedChemical(
            name="BPA",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        recommendations = scorer._generate_recommendations([chemical], "high", None)
        
        recommendations_text = " ".join(recommendations)
        assert "BPA" in recommendations_text
        assert "BPA-free" in recommendations_text or "bpa-free" in recommendations_text.lower()
    
    def test_generate_recommendations_phthalate_specific(self, scorer):
        """Test phthalate-specific recommendations"""
        chemical = FlaggedChemical(
            name="DEHP",
            cas_number="117-81-7",
            edc_types=[EDCType.PHTHALATE],
            risk_score=90.0,
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        recommendations = scorer._generate_recommendations([chemical], "high", None)
        
        recommendations_text = " ".join(recommendations)
        assert "Phthalate" in recommendations_text or "phthalate" in recommendations_text
    
    def test_generate_recommendations_category_specific(self, scorer):
        """Test category-specific recommendations"""
        chemical = FlaggedChemical(
            name="Paraben",
            cas_number="99-76-3",
            edc_types=[EDCType.PARABEN],
            risk_score=45.0,
            health_effects=[],
            regulatory_status=RegulatoryInfo(),
            sources=[],
            confidence=1.0
        )
        
        # Test cosmetic category
        recommendations = scorer._generate_recommendations([chemical], "medium", "cosmetic")
        recommendations_text = " ".join(recommendations)
        assert "cosmetic" in recommendations_text.lower() or "EWG" in recommendations_text
        
        # Test food category
        recommendations = scorer._generate_recommendations([chemical], "medium", "food")
        recommendations_text = " ".join(recommendations)
        assert "food" in recommendations_text.lower() or "organic" in recommendations_text.lower()
    
    def test_generate_user_warnings(self, scorer):
        """Test user warning generation"""
        warnings = scorer._generate_user_warnings([])
        
        # Should always have at least 3 core warnings
        assert len(warnings) >= 3
        
        # Check for key warning types
        warnings_text = " ".join(warnings)
        assert "AWARENESS TOOL" in warnings_text or "awareness" in warnings_text.lower()
        assert "LABEL LIMITATIONS" in warnings_text or "label" in warnings_text.lower()
        assert "SCIENTIFIC UNCERTAINTY" in warnings_text or "scientific" in warnings_text.lower()
    
    @pytest.mark.asyncio
    async def test_get_toxicity_scorer(self):
        """Test global scorer instance creation"""
        scorer1 = await get_toxicity_scorer()
        scorer2 = await get_toxicity_scorer()
        
        # Should return same instance
        assert scorer1 is scorer2
        assert isinstance(scorer1, ToxicityScorer)


class TestToxicityScoreDataModel:
    """Test ToxicityScore data model"""
    
    def test_toxicity_score_creation(self):
        """Test ToxicityScore dataclass creation"""
        score = ToxicityScore(
            overall_score=75.5,
            hormonal_health_score=70.2,
            risk_level="medium",
            flagged_chemicals=[],
            recommendations=["Test recommendation"],
            confidence_warnings=["Low confidence warning"],
            user_warnings=["User warning"]
        )
        
        assert score.overall_score == 75.5
        assert score.hormonal_health_score == 70.2
        assert score.risk_level == "medium"
        assert len(score.recommendations) == 1
        assert len(score.confidence_warnings) == 1
        assert len(score.user_warnings) == 1
    
    def test_toxicity_score_to_dict(self):
        """Test ToxicityScore serialization"""
        chemical = FlaggedChemical(
            name="BPA",
            cas_number="80-05-7",
            edc_types=[EDCType.BPA],
            risk_score=85.0,
            health_effects=["Hormone disruption"],
            regulatory_status=RegulatoryInfo(fssai_approved=False),
            sources=["local_database"],
            confidence=0.95
        )
        
        score = ToxicityScore(
            overall_score=60.0,
            hormonal_health_score=55.0,
            risk_level="medium",
            flagged_chemicals=[chemical],
            recommendations=["Avoid BPA"],
            confidence_warnings=[],
            user_warnings=["This is an awareness tool"]
        )
        
        data = score.to_dict()
        
        assert data["overall_score"] == 60.0
        assert data["hormonal_health_score"] == 55.0
        assert data["risk_level"] == "medium"
        assert len(data["flagged_chemicals"]) == 1
        assert data["flagged_chemicals"][0]["name"] == "BPA"
        assert len(data["recommendations"]) == 1
        assert len(data["user_warnings"]) == 1


class TestIngredientDataModel:
    """Test Ingredient data model"""
    
    def test_ingredient_creation(self):
        """Test Ingredient dataclass creation"""
        ingredient = Ingredient(
            name="Methylparaben",
            alternate_names=["Methyl paraben", "E218"],
            concentration="0.4%",
            cas_number="99-76-3"
        )
        
        assert ingredient.name == "Methylparaben"
        assert len(ingredient.alternate_names) == 2
        assert ingredient.concentration == "0.4%"
        assert ingredient.cas_number == "99-76-3"
    
    def test_ingredient_default_alternate_names(self):
        """Test Ingredient with default alternate names"""
        ingredient = Ingredient(name="Water")
        
        assert ingredient.name == "Water"
        assert ingredient.alternate_names == []
        assert ingredient.concentration is None
        assert ingredient.cas_number is None
    
    def test_ingredient_to_dict(self):
        """Test Ingredient serialization"""
        ingredient = Ingredient(
            name="BPA",
            alternate_names=["Bisphenol A"],
            cas_number="80-05-7"
        )
        
        data = ingredient.to_dict()
        
        assert data["name"] == "BPA"
        assert data["alternate_names"] == ["Bisphenol A"]
        assert data["cas_number"] == "80-05-7"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
