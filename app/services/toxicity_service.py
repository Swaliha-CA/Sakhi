"""Toxicity Scoring Service with database integration and chemical entity resolution"""
import hashlib
import json
import re
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from difflib import SequenceMatcher

import httpx
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


class EDCType(str, Enum):
    """Types of Endocrine Disrupting Chemicals"""
    BPA = "bpa"
    PHTHALATE = "phthalate"
    PARABEN = "paraben"
    ORGANOCHLORINE = "organochlorine"
    HEAVY_METAL = "heavy_metal"
    PFAS = "pfas"
    UNKNOWN = "unknown"


@dataclass
class ChemicalIdentifier:
    """Chemical identification data"""
    cas_number: Optional[str] = None
    smiles: Optional[str] = None
    inchi_key: Optional[str] = None
    common_names: List[str] = None
    
    def __post_init__(self):
        if self.common_names is None:
            self.common_names = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegulatoryInfo:
    """Regulatory status information"""
    fssai_approved: Optional[bool] = None
    fssai_limit: Optional[str] = None
    epa_status: Optional[str] = None
    eu_status: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FlaggedChemical:
    """Information about a flagged EDC chemical"""
    name: str
    cas_number: Optional[str]
    edc_types: List[EDCType]
    risk_score: float  # 0-100, higher = more risky
    health_effects: List[str]
    regulatory_status: RegulatoryInfo
    sources: List[str]  # Database sources
    confidence: float  # Matching confidence 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cas_number": self.cas_number,
            "edc_types": [edc.value for edc in self.edc_types],
            "risk_score": self.risk_score,
            "health_effects": self.health_effects,
            "regulatory_status": self.regulatory_status.to_dict(),
            "sources": self.sources,
            "confidence": self.confidence
        }


@dataclass
class Ingredient:
    """Ingredient information"""
    name: str
    alternate_names: List[str] = None
    concentration: Optional[str] = None
    cas_number: Optional[str] = None
    
    def __post_init__(self):
        if self.alternate_names is None:
            self.alternate_names = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToxicityScore:
    """Comprehensive toxicity scoring result"""
    overall_score: float  # 0-100, higher is safer
    hormonal_health_score: float  # PCOS-specific score, 0-100, higher is safer
    risk_level: str  # "low", "medium", "high", "critical"
    flagged_chemicals: List[FlaggedChemical]
    recommendations: List[str]
    confidence_warnings: List[str]  # Warnings about low confidence matches
    user_warnings: List[str]  # General warnings about limitations
    alternatives: Optional[List[Dict[str, Any]]] = None  # Alternative product suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "overall_score": self.overall_score,
            "hormonal_health_score": self.hormonal_health_score,
            "risk_level": self.risk_level,
            "flagged_chemicals": [chem.to_dict() for chem in self.flagged_chemicals],
            "recommendations": self.recommendations,
            "confidence_warnings": self.confidence_warnings,
            "user_warnings": self.user_warnings
        }
        if self.alternatives is not None:
            result["alternatives"] = self.alternatives
        return result


class ChemicalEntityResolver:
    """
    NLP-driven chemical entity resolution pipeline
    Maps ingredient names to CAS numbers/SMILES/InChIKeys
    
    CRITICAL: Indian labels rarely list CAS numbers. This resolver is mandatory
    to identify "known unknowns" and prevent false negatives on hazardous materials.
    """
    
    def __init__(self):
        """Initialize chemical entity resolver"""
        self.http_client: Optional[httpx.AsyncClient] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # Common chemical name mappings (Indian context)
        self.indian_name_mappings = {
            # Parabens
            "methyl paraben": "methylparaben",
            "ethyl paraben": "ethylparaben",
            "propyl paraben": "propylparaben",
            "butyl paraben": "butylparaben",
            
            # Phthalates
            "diethyl phthalate": "dep",
            "dibutyl phthalate": "dbp",
            "di(2-ethylhexyl) phthalate": "dehp",
            "diisononyl phthalate": "dinp",
            "diisodecyl phthalate": "didp",
            
            # BPA variants
            "bisphenol a": "bpa",
            "bisphenol s": "bps",
            "bisphenol f": "bpf",
            
            # Heavy metals
            "lead": "pb",
            "mercury": "hg",
            "cadmium": "cd",
            "arsenic": "as",
            
            # Common Indian names
            "kumkum": "vermillion",
            "sindoor": "vermillion",
            "kajal": "kohl",
            "surma": "kohl",
        }
    
    async def connect(self):
        """Initialize HTTP client and Redis connection"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Chemical entity resolver connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None
    
    async def disconnect(self):
        """Close connections"""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.close()
    
    def _normalize_name(self, name: str) -> str:
        """Normalize chemical name for matching"""
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'\b(ci|fd&c|d&c|e\d+)\b', '', normalized)
        
        # Remove special characters but keep hyphens and parentheses
        normalized = re.sub(r'[^\w\s\-\(\)]', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Check for Indian name mappings
        if normalized in self.indian_name_mappings:
            normalized = self.indian_name_mappings[normalized]
        
        return normalized
    
    def _bio_sim_similarity(self, str1: str, str2: str) -> float:
        """
        Bio-SIM algorithm for fuzzy matching of chemical names
        
        Uses sequence matching with chemical-specific adjustments:
        - Prioritizes exact prefix matches (common in chemical nomenclature)
        - Handles common abbreviations
        - Accounts for parenthetical variations
        """
        # Normalize both strings
        s1 = self._normalize_name(str1)
        s2 = self._normalize_name(str2)
        
        # Exact match
        if s1 == s2:
            return 1.0
        
        # Check if one is abbreviation of other
        if s1 in s2 or s2 in s1:
            return 0.95
        
        # Use SequenceMatcher for fuzzy matching
        base_similarity = SequenceMatcher(None, s1, s2).ratio()
        
        # Boost score for matching prefixes (important in chemical names)
        prefix_len = min(len(s1), len(s2), 5)
        if s1[:prefix_len] == s2[:prefix_len]:
            base_similarity = min(1.0, base_similarity + 0.1)
        
        return base_similarity
    
    async def _get_cached_identifier(self, name: str) -> Optional[ChemicalIdentifier]:
        """Get cached chemical identifier from Redis"""
        if not self.redis_client:
            return None
        
        cache_key = f"chem:entity:{hashlib.md5(name.lower().encode()).hexdigest()}"
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for chemical: {name}")
                data = json.loads(cached)
                return ChemicalIdentifier(**data)
        except Exception as e:
            logger.warning(f"Failed to get cached identifier: {e}")
        
        return None
    
    async def _cache_identifier(self, name: str, identifier: ChemicalIdentifier):
        """Cache chemical identifier in Redis (7-day TTL)"""
        if not self.redis_client:
            return
        
        cache_key = f"chem:entity:{hashlib.md5(name.lower().encode()).hexdigest()}"
        
        try:
            await self.redis_client.setex(
                cache_key,
                settings.CHEMICAL_CACHE_TTL,
                json.dumps(identifier.to_dict())
            )
            logger.debug(f"Cached identifier for: {name}")
        except Exception as e:
            logger.warning(f"Failed to cache identifier: {e}")
    
    async def resolve_to_cas(self, ingredient_name: str) -> Tuple[Optional[str], float]:
        """
        Resolve ingredient name to CAS number
        
        Args:
            ingredient_name: Common or trade name of ingredient
        
        Returns:
            Tuple of (CAS number, confidence score)
        """
        # Check cache first
        cached = await self._get_cached_identifier(ingredient_name)
        if cached and cached.cas_number:
            return cached.cas_number, 1.0
        
        # Try PubChem API for name resolution
        try:
            identifier = await self._query_pubchem(ingredient_name)
            if identifier and identifier.cas_number:
                await self._cache_identifier(ingredient_name, identifier)
                return identifier.cas_number, 0.9
        except Exception as e:
            logger.warning(f"PubChem query failed for {ingredient_name}: {e}")
        
        # Try CompTox API
        try:
            identifier = await self._query_comptox(ingredient_name)
            if identifier and identifier.cas_number:
                await self._cache_identifier(ingredient_name, identifier)
                return identifier.cas_number, 0.85
        except Exception as e:
            logger.warning(f"CompTox query failed for {ingredient_name}: {e}")
        
        # Fallback: Check local database of common chemicals
        cas_number = self._lookup_local_database(ingredient_name)
        if cas_number:
            return cas_number, 0.7
        
        logger.info(f"Could not resolve CAS number for: {ingredient_name}")
        return None, 0.0
    
    async def _query_pubchem(self, name: str) -> Optional[ChemicalIdentifier]:
        """Query PubChem API for chemical identification"""
        if not self.http_client:
            return None
        
        normalized_name = self._normalize_name(name)
        
        try:
            # Search by name
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{normalized_name}/property/IUPACName,MolecularFormula,InChIKey/JSON"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                properties = data.get("PropertyTable", {}).get("Properties", [])
                
                if properties:
                    prop = properties[0]
                    
                    # Get CAS number from synonyms
                    cid = prop.get("CID")
                    cas_number = await self._get_cas_from_pubchem_cid(cid)
                    
                    return ChemicalIdentifier(
                        cas_number=cas_number,
                        inchi_key=prop.get("InChIKey"),
                        common_names=[name, normalized_name]
                    )
        
        except Exception as e:
            logger.debug(f"PubChem query error: {e}")
        
        return None
    
    async def _get_cas_from_pubchem_cid(self, cid: int) -> Optional[str]:
        """Get CAS number from PubChem CID"""
        if not self.http_client or not cid:
            return None
        
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                synonyms = data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
                
                # Look for CAS number pattern (XXX-XX-X or XXXXX-XX-X)
                cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
                for syn in synonyms:
                    if cas_pattern.match(syn):
                        return syn
        
        except Exception as e:
            logger.debug(f"CAS lookup error: {e}")
        
        return None
    
    async def _query_comptox(self, name: str) -> Optional[ChemicalIdentifier]:
        """Query EPA CompTox Dashboard API"""
        # Note: CompTox API requires authentication
        # This is a placeholder for the actual implementation
        # In production, use settings.COMPTOX_API_KEY
        
        if not settings.COMPTOX_API_KEY:
            logger.debug("CompTox API key not configured")
            return None
        
        # TODO: Implement actual CompTox API query
        # For now, return None
        return None
    
    def _lookup_local_database(self, name: str) -> Optional[str]:
        """
        Lookup CAS number in local database of common chemicals
        
        This is a fallback for common ingredients when APIs fail
        """
        # Common chemicals database (subset for demonstration)
        local_db = {
            "water": "7732-18-5",
            "glycerin": "56-81-5",
            "glycerol": "56-81-5",
            "propylene glycol": "57-55-6",
            "methylparaben": "99-76-3",
            "ethylparaben": "120-47-8",
            "propylparaben": "94-13-3",
            "butylparaben": "94-26-8",
            "bpa": "80-05-7",
            "bisphenol a": "80-05-7",
            "dehp": "117-81-7",
            "dbp": "84-74-2",
            "dep": "84-66-2",
            "lead": "7439-92-1",
            "mercury": "7439-97-6",
            "cadmium": "7440-43-9",
            "arsenic": "7440-38-2",
            "triclosan": "3380-34-5",
            "triclocarban": "101-20-2",
            "formaldehyde": "50-00-0",
            "toluene": "108-88-3",
            "benzene": "71-43-2",
        }
        
        normalized = self._normalize_name(name)
        
        # Exact match
        if normalized in local_db:
            return local_db[normalized]
        
        # Fuzzy match with high threshold
        best_match = None
        best_score = 0.0
        
        for db_name, cas in local_db.items():
            score = self._bio_sim_similarity(normalized, db_name)
            if score > best_score and score >= 0.85:  # High threshold for safety
                best_score = score
                best_match = cas
        
        return best_match


class ToxicityDatabaseClient:
    """Client for querying toxicity databases"""
    
    def __init__(self):
        """Initialize database client"""
        self.http_client: Optional[httpx.AsyncClient] = None
        self.redis_client: Optional[redis.Redis] = None
        self.entity_resolver = ChemicalEntityResolver()
    
    async def connect(self):
        """Initialize connections"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await self.entity_resolver.connect()
        
        try:
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Toxicity database client connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None
    
    async def disconnect(self):
        """Close connections"""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.close()
        await self.entity_resolver.disconnect()
    
    async def _get_cached_chemical_info(self, cas_number: str) -> Optional[Dict[str, Any]]:
        """Get cached chemical information from Redis"""
        if not self.redis_client:
            return None
        
        cache_key = f"chem:info:{cas_number}"
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for CAS: {cas_number}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached chemical info: {e}")
        
        return None
    
    async def _cache_chemical_info(self, cas_number: str, info: Dict[str, Any]):
        """Cache chemical information in Redis (7-day TTL)"""
        if not self.redis_client:
            return
        
        cache_key = f"chem:info:{cas_number}"
        
        try:
            await self.redis_client.setex(
                cache_key,
                settings.CHEMICAL_CACHE_TTL,
                json.dumps(info)
            )
            logger.debug(f"Cached info for CAS: {cas_number}")
        except Exception as e:
            logger.warning(f"Failed to cache chemical info: {e}")
    
    async def query_comptox(self, cas_number: str) -> Optional[Dict[str, Any]]:
        """
        Query EPA CompTox Dashboard for chemical toxicity data
        
        Args:
            cas_number: CAS Registry Number
        
        Returns:
            Dictionary with toxicity information
        """
        # Check cache first
        cached = await self._get_cached_chemical_info(cas_number)
        if cached and "comptox" in cached.get("sources", []):
            return cached
        
        if not settings.COMPTOX_API_KEY:
            logger.debug("CompTox API key not configured")
            return None
        
        # TODO: Implement actual CompTox API query
        # Placeholder for demonstration
        logger.info(f"Would query CompTox for CAS: {cas_number}")
        
        return None
    
    async def query_openfoodtox(self, cas_number: str) -> Optional[Dict[str, Any]]:
        """
        Query OpenFoodTox database for food additive safety data
        
        Args:
            cas_number: CAS Registry Number
        
        Returns:
            Dictionary with food safety information
        """
        # Check cache first
        cached = await self._get_cached_chemical_info(cas_number)
        if cached and "openfoodtox" in cached.get("sources", []):
            return cached
        
        if not self.http_client:
            return None
        
        try:
            # OpenFoodTox API endpoint (placeholder - actual API may differ)
            url = f"{settings.OPENFOODTOX_API_URL}/chemical/{cas_number}"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"OpenFoodTox data retrieved for CAS: {cas_number}")
                return data
        
        except Exception as e:
            logger.debug(f"OpenFoodTox query failed: {e}")
        
        return None
    
    async def query_fssai(self, cas_number: str, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """
        Query FSSAI database for India-specific regulatory information
        
        Args:
            cas_number: CAS Registry Number
            ingredient_name: Common name of ingredient
        
        Returns:
            Dictionary with FSSAI regulatory status
        """
        # Check cache first
        cached = await self._get_cached_chemical_info(cas_number)
        if cached and "fssai" in cached.get("sources", []):
            return cached
        
        if not settings.FSSAI_API_KEY:
            logger.debug("FSSAI API key not configured")
            return None
        
        # TODO: Implement actual FSSAI API query
        # Placeholder for demonstration
        logger.info(f"Would query FSSAI for CAS: {cas_number}, name: {ingredient_name}")
        
        return None
    
    async def get_edc_info(self, ingredient_name: str) -> Optional[FlaggedChemical]:
        """
        Get comprehensive EDC information for an ingredient
        
        Args:
            ingredient_name: Name of the ingredient
        
        Returns:
            FlaggedChemical object if ingredient is an EDC, None otherwise
        """
        # Step 1: Resolve ingredient name to CAS number
        cas_number, confidence = await self.entity_resolver.resolve_to_cas(ingredient_name)
        
        if not cas_number:
            logger.info(f"Could not resolve ingredient to CAS: {ingredient_name}")
            return None
        
        logger.info(f"Resolved '{ingredient_name}' to CAS: {cas_number} (confidence: {confidence:.2f})")
        
        # Step 2: Query toxicity databases
        comptox_data = await self.query_comptox(cas_number)
        openfoodtox_data = await self.query_openfoodtox(cas_number)
        fssai_data = await self.query_fssai(cas_number, ingredient_name)
        
        # Step 3: Aggregate data and determine if it's an EDC
        # For now, use local knowledge base (in production, use actual API data)
        edc_info = self._get_local_edc_info(ingredient_name, cas_number)
        
        if edc_info:
            edc_info.confidence = confidence
            return edc_info
        
        return None
    
    def _get_local_edc_info(self, name: str, cas_number: str) -> Optional[FlaggedChemical]:
        """
        Get EDC information from local knowledge base
        
        This is a fallback/supplement to API data
        """
        # Known EDCs database (subset for demonstration)
        edc_database = {
            "99-76-3": {  # Methylparaben
                "name": "Methylparaben",
                "edc_types": [EDCType.PARABEN],
                "risk_score": 45.0,
                "health_effects": ["Endocrine disruption", "Potential reproductive effects"],
                "fssai_approved": True,
                "fssai_limit": "0.4% (as paraben)"
            },
            "80-05-7": {  # BPA
                "name": "Bisphenol A (BPA)",
                "edc_types": [EDCType.BPA],
                "risk_score": 85.0,
                "health_effects": ["Hormone disruption", "PCOS risk factor", "Reproductive toxicity"],
                "fssai_approved": False,
                "fssai_limit": "Banned in baby products"
            },
            "117-81-7": {  # DEHP
                "name": "Di(2-ethylhexyl) phthalate (DEHP)",
                "edc_types": [EDCType.PHTHALATE],
                "risk_score": 90.0,
                "health_effects": ["Endocrine disruption", "Reproductive toxicity", "PPD risk factor"],
                "fssai_approved": False,
                "fssai_limit": "Banned in food contact materials"
            },
            "84-74-2": {  # DBP
                "name": "Dibutyl phthalate (DBP)",
                "edc_types": [EDCType.PHTHALATE],
                "risk_score": 80.0,
                "health_effects": ["Hormone disruption", "Reproductive effects"],
                "fssai_approved": False,
                "fssai_limit": "Restricted"
            },
            "7439-92-1": {  # Lead
                "name": "Lead",
                "edc_types": [EDCType.HEAVY_METAL],
                "risk_score": 95.0,
                "health_effects": ["Neurotoxicity", "Developmental effects", "Hormone disruption"],
                "fssai_approved": False,
                "fssai_limit": "Banned in cosmetics"
            },
            "3380-34-5": {  # Triclosan
                "name": "Triclosan",
                "edc_types": [EDCType.ORGANOCHLORINE],
                "risk_score": 70.0,
                "health_effects": ["Endocrine disruption", "Thyroid effects", "Antibiotic resistance"],
                "fssai_approved": False,
                "fssai_limit": "Banned in personal care products"
            },
        }
        
        if cas_number in edc_database:
            data = edc_database[cas_number]
            
            return FlaggedChemical(
                name=data["name"],
                cas_number=cas_number,
                edc_types=data["edc_types"],
                risk_score=data["risk_score"],
                health_effects=data["health_effects"],
                regulatory_status=RegulatoryInfo(
                    fssai_approved=data.get("fssai_approved"),
                    fssai_limit=data.get("fssai_limit")
                ),
                sources=["local_database"],
                confidence=1.0  # Will be updated by caller
            )
        
        return None


# Global toxicity database client
toxicity_db_client = ToxicityDatabaseClient()


class ToxicityScorer:
    """
    Toxicity scoring algorithm for product safety assessment
    
    Implements:
    - Overall toxicity scoring (0-100 scale, higher is safer)
    - PCOS-specific hormonal health scoring with penalties for hormone disruptors
    - Risk level classification (low/medium/high/critical)
    - Confidence threshold warnings (<85%)
    - User warnings about scientific limitations
    """
    
    # PCOS-aggravating EDC types with penalty multipliers
    PCOS_PENALTY_MULTIPLIERS = {
        EDCType.BPA: 1.5,           # Strong PCOS correlation
        EDCType.PHTHALATE: 1.4,     # Hormone disruption, PPD risk
        EDCType.ORGANOCHLORINE: 1.3, # Endocrine disruption
        EDCType.HEAVY_METAL: 1.2,   # Developmental and hormonal effects
        EDCType.PFAS: 1.3,          # Endocrine disruption
        EDCType.PARABEN: 1.1,       # Mild endocrine effects
        EDCType.UNKNOWN: 1.0        # No penalty
    }
    
    # Risk level thresholds (based on overall score, lower score = higher risk)
    RISK_THRESHOLDS = {
        "low": 70,      # Score >= 70: Low risk
        "medium": 50,   # Score >= 50: Medium risk
        "high": 30,     # Score >= 30: High risk
        "critical": 0   # Score < 30: Critical risk
    }
    
    # Confidence threshold for warnings
    CONFIDENCE_THRESHOLD = 0.85
    
    def __init__(self, db_client: ToxicityDatabaseClient):
        """
        Initialize toxicity scorer
        
        Args:
            db_client: ToxicityDatabaseClient instance for querying EDC data
        """
        self.db_client = db_client
    
    async def score_product(
        self,
        ingredients: List[Ingredient],
        product_category: Optional[str] = None,
        include_alternatives: bool = False,
        db_session: Optional[Any] = None,
        user_region: Optional[str] = None,
        price_preference: Optional[str] = None
    ) -> ToxicityScore:
        """
        Calculate comprehensive toxicity score for a product
        
        Args:
            ingredients: List of product ingredients
            product_category: Optional product category (cosmetic, food, etc.)
            include_alternatives: Whether to include alternative product suggestions
            db_session: Database session for querying alternatives
            user_region: User's region for availability filtering
            price_preference: User's price preference
        
        Returns:
            ToxicityScore with overall score, hormonal health score, and risk assessment
        """
        logger.info(f"Scoring product with {len(ingredients)} ingredients")
        
        # Step 1: Identify EDCs in ingredients
        flagged_chemicals: List[FlaggedChemical] = []
        low_confidence_matches: List[str] = []
        
        for ingredient in ingredients:
            edc_info = await self.db_client.get_edc_info(ingredient.name)
            
            if edc_info:
                flagged_chemicals.append(edc_info)
                
                # Track low confidence matches
                if edc_info.confidence < self.CONFIDENCE_THRESHOLD:
                    low_confidence_matches.append(
                        f"{ingredient.name} (confidence: {edc_info.confidence:.0%})"
                    )
                
                logger.info(
                    f"Flagged EDC: {edc_info.name} "
                    f"(risk: {edc_info.risk_score:.1f}, confidence: {edc_info.confidence:.2f})"
                )
        
        # Step 2: Calculate overall toxicity score
        overall_score = self._calculate_overall_score(flagged_chemicals, len(ingredients))
        
        # Step 3: Calculate PCOS-specific hormonal health score
        hormonal_health_score = self._calculate_hormonal_health_score(
            flagged_chemicals,
            len(ingredients)
        )
        
        # Step 4: Determine risk level
        risk_level = self._classify_risk_level(overall_score)
        
        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(
            flagged_chemicals,
            risk_level,
            product_category
        )
        
        # Step 6: Generate confidence warnings
        confidence_warnings = []
        if low_confidence_matches:
            confidence_warnings.append(
                f"Low confidence ingredient matching detected for: {', '.join(low_confidence_matches)}. "
                "Results may be less accurate."
            )
        
        # Step 7: Generate user warnings about limitations
        user_warnings = self._generate_user_warnings(flagged_chemicals)
        
        # Step 8: Find alternative products if requested
        alternatives = None
        if include_alternatives and db_session and product_category:
            alternatives = await self._find_alternatives(
                db_session,
                product_category,
                hormonal_health_score,
                flagged_chemicals,
                user_region,
                price_preference
            )
        
        logger.info(
            f"Scoring complete - Overall: {overall_score:.1f}, "
            f"Hormonal Health: {hormonal_health_score:.1f}, "
            f"Risk: {risk_level}, "
            f"Flagged: {len(flagged_chemicals)}"
        )
        
        return ToxicityScore(
            overall_score=overall_score,
            hormonal_health_score=hormonal_health_score,
            risk_level=risk_level,
            flagged_chemicals=flagged_chemicals,
            recommendations=recommendations,
            confidence_warnings=confidence_warnings,
            user_warnings=user_warnings,
            alternatives=alternatives
        )
    
    def _calculate_overall_score(
        self,
        flagged_chemicals: List[FlaggedChemical],
        total_ingredients: int
    ) -> float:
        """
        Calculate overall toxicity score (0-100, higher is safer)
        
        Algorithm:
        1. Start with perfect score (100)
        2. Subtract weighted risk scores for each EDC
        3. Weight by concentration if available (not implemented yet - labels don't list concentrations)
        4. Normalize by total ingredients
        
        Args:
            flagged_chemicals: List of identified EDCs
            total_ingredients: Total number of ingredients in product
        
        Returns:
            Overall score (0-100)
        """
        if not flagged_chemicals:
            return 100.0  # Perfect score if no EDCs found
        
        # Start with perfect score
        score = 100.0
        
        # Calculate total risk penalty
        total_risk = 0.0
        for chemical in flagged_chemicals:
            # Weight risk by confidence (lower confidence = lower impact)
            weighted_risk = chemical.risk_score * chemical.confidence
            total_risk += weighted_risk
        
        # Average risk per flagged chemical
        avg_risk = total_risk / len(flagged_chemicals)
        
        # Penalty factor based on proportion of EDCs in product
        edc_proportion = len(flagged_chemicals) / max(total_ingredients, 1)
        proportion_penalty = 1.0 + (edc_proportion * 0.5)  # Up to 50% increase in penalty
        
        # Apply penalty
        penalty = avg_risk * proportion_penalty
        score = max(0.0, score - penalty)
        
        return round(score, 1)
    
    def _calculate_hormonal_health_score(
        self,
        flagged_chemicals: List[FlaggedChemical],
        total_ingredients: int
    ) -> float:
        """
        Calculate PCOS-specific hormonal health score (0-100, higher is safer)
        
        Applies additional penalties for EDC types known to aggravate PCOS:
        - BPA: 1.5x penalty (strong PCOS correlation)
        - Phthalates: 1.4x penalty (hormone disruption, PPD risk)
        - Organochlorines: 1.3x penalty (endocrine disruption)
        - Heavy metals: 1.2x penalty (developmental effects)
        
        Args:
            flagged_chemicals: List of identified EDCs
            total_ingredients: Total number of ingredients in product
        
        Returns:
            Hormonal health score (0-100)
        """
        if not flagged_chemicals:
            return 100.0  # Perfect score if no EDCs found
        
        # Start with perfect score
        score = 100.0
        
        # Calculate total risk with PCOS penalties
        total_risk = 0.0
        for chemical in flagged_chemicals:
            # Base risk weighted by confidence
            weighted_risk = chemical.risk_score * chemical.confidence
            
            # Apply PCOS penalty multipliers for each EDC type
            max_penalty = 1.0
            for edc_type in chemical.edc_types:
                penalty_multiplier = self.PCOS_PENALTY_MULTIPLIERS.get(edc_type, 1.0)
                max_penalty = max(max_penalty, penalty_multiplier)
            
            # Apply the highest penalty multiplier
            pcos_weighted_risk = weighted_risk * max_penalty
            total_risk += pcos_weighted_risk
        
        # Average risk per flagged chemical
        avg_risk = total_risk / len(flagged_chemicals)
        
        # Penalty factor based on proportion of EDCs in product
        edc_proportion = len(flagged_chemicals) / max(total_ingredients, 1)
        proportion_penalty = 1.0 + (edc_proportion * 0.5)
        
        # Apply penalty
        penalty = avg_risk * proportion_penalty
        score = max(0.0, score - penalty)
        
        return round(score, 1)
    
    def _classify_risk_level(self, overall_score: float) -> str:
        """
        Classify risk level based on overall score
        
        Thresholds:
        - Low: Score >= 70
        - Medium: Score >= 50
        - High: Score >= 30
        - Critical: Score < 30
        
        Args:
            overall_score: Overall toxicity score (0-100)
        
        Returns:
            Risk level string
        """
        if overall_score >= self.RISK_THRESHOLDS["low"]:
            return "low"
        elif overall_score >= self.RISK_THRESHOLDS["medium"]:
            return "medium"
        elif overall_score >= self.RISK_THRESHOLDS["high"]:
            return "high"
        else:
            return "critical"
    
    def _generate_recommendations(
        self,
        flagged_chemicals: List[FlaggedChemical],
        risk_level: str,
        product_category: Optional[str]
    ) -> List[str]:
        """
        Generate personalized recommendations based on flagged chemicals
        
        Args:
            flagged_chemicals: List of identified EDCs
            risk_level: Classified risk level
            product_category: Product category
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not flagged_chemicals:
            recommendations.append("No EDCs detected. This product appears safe based on available data.")
            return recommendations
        
        # Risk-level specific recommendations
        if risk_level == "critical":
            recommendations.append(
                "⚠️ CRITICAL: This product contains high-risk EDCs. "
                "We strongly recommend avoiding this product, especially if you have PCOS or are planning pregnancy."
            )
        elif risk_level == "high":
            recommendations.append(
                "⚠️ HIGH RISK: This product contains concerning levels of EDCs. "
                "Consider switching to safer alternatives."
            )
        elif risk_level == "medium":
            recommendations.append(
                "⚠️ MODERATE RISK: This product contains some EDCs. "
                "Limit use and consider alternatives when possible."
            )
        else:  # low
            recommendations.append(
                "ℹ️ LOW RISK: This product contains minimal EDCs. "
                "Generally safe for use, but monitor cumulative exposure."
            )
        
        # EDC-type specific recommendations
        edc_types_found = set()
        for chemical in flagged_chemicals:
            edc_types_found.update(chemical.edc_types)
        
        if EDCType.BPA in edc_types_found:
            recommendations.append(
                "🔴 BPA detected: Strong PCOS risk factor. "
                "Look for 'BPA-free' alternatives. Avoid heating products containing BPA."
            )
        
        if EDCType.PHTHALATE in edc_types_found:
            recommendations.append(
                "🔴 Phthalates detected: Linked to hormone disruption and postpartum depression risk. "
                "Choose 'phthalate-free' products, especially during pregnancy."
            )
        
        if EDCType.PARABEN in edc_types_found:
            recommendations.append(
                "🟡 Parabens detected: Mild endocrine effects. "
                "Consider 'paraben-free' alternatives if you have hormonal sensitivities."
            )
        
        if EDCType.HEAVY_METAL in edc_types_found:
            recommendations.append(
                "🔴 Heavy metals detected: Serious health risk. "
                "Avoid this product immediately. Check for lead, mercury, or cadmium."
            )
        
        if EDCType.ORGANOCHLORINE in edc_types_found:
            recommendations.append(
                "🔴 Organochlorines detected: Endocrine disruptors. "
                "Avoid products with triclosan or similar antibacterial agents."
            )
        
        if EDCType.PFAS in edc_types_found:
            recommendations.append(
                "🔴 PFAS detected: 'Forever chemicals' that accumulate in the body. "
                "Avoid products with PFAS, especially in food packaging and cosmetics."
            )
        
        # Category-specific recommendations
        if product_category:
            if product_category.lower() in ["cosmetic", "personal_care"]:
                recommendations.append(
                    "💡 For cosmetics: Look for products certified by EWG Skin Deep or similar databases."
                )
            elif product_category.lower() == "food":
                recommendations.append(
                    "💡 For food: Choose organic when possible and avoid plastic packaging that may leach EDCs."
                )
        
        return recommendations
    
    def _generate_user_warnings(self, flagged_chemicals: List[FlaggedChemical]) -> List[str]:
        """
        Generate warnings about scientific limitations
        
        CRITICAL: Product labels don't list EDC concentrations or packaging leachates.
        Scoring "clinical risk" from OCR alone is scientifically fragile.
        
        Args:
            flagged_chemicals: List of identified EDCs
        
        Returns:
            List of warning strings
        """
        warnings = [
            "⚠️ AWARENESS TOOL, NOT DIAGNOSTIC: This analysis is for educational purposes only "
            "and should not be used as medical advice or clinical diagnosis.",
            
            "📋 LABEL LIMITATIONS: Product labels typically do not list EDC concentrations or "
            "chemicals that may leach from packaging materials. Actual exposure may differ from this assessment.",
            
            "🔬 SCIENTIFIC UNCERTAINTY: While EDC-health links are well-established in research, "
            "individual risk varies based on exposure duration, frequency, and personal health factors.",
        ]
        
        if flagged_chemicals:
            warnings.append(
                "💡 RECOMMENDATION: Use this tool to build awareness and make informed choices, "
                "but consult healthcare professionals for personalized medical advice."
            )
        
        return warnings
    
    async def _find_alternatives(
        self,
        db_session: Any,
        product_category: str,
        current_score: float,
        flagged_chemicals: List[FlaggedChemical],
        user_region: Optional[str] = None,
        price_preference: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find alternative products using the alternative product service
        
        Args:
            db_session: Database session
            product_category: Product category
            current_score: Current product's hormonal health score
            flagged_chemicals: List of flagged EDCs
            user_region: User's region
            price_preference: User's price preference
        
        Returns:
            List of alternative product dictionaries
        """
        try:
            from app.services.alternative_product_service import AlternativeProductService
            
            # Extract EDC types from flagged chemicals
            flagged_edc_types = []
            for chemical in flagged_chemicals:
                flagged_edc_types.extend([edc.value for edc in chemical.edc_types])
            
            # Remove duplicates
            flagged_edc_types = list(set(flagged_edc_types))
            
            # Create service instance
            alt_service = AlternativeProductService(db_session)
            
            # Find alternatives
            alternatives = await alt_service.find_alternatives(
                product_category=product_category,
                current_score=current_score,
                flagged_edcs=flagged_edc_types if flagged_edc_types else None,
                price_preference=price_preference,
                region=user_region,
                limit=5
            )
            
            # Convert to dictionaries
            return [alt.to_dict() for alt in alternatives]
        
        except Exception as e:
            logger.error(f"Failed to find alternatives: {e}")
            return []


# Global toxicity scorer instance
toxicity_scorer: Optional[ToxicityScorer] = None


async def get_toxicity_scorer() -> ToxicityScorer:
    """
    Get or create global toxicity scorer instance
    
    Returns:
        ToxicityScorer instance
    """
    global toxicity_scorer
    
    if toxicity_scorer is None:
        # Ensure database client is connected
        if not toxicity_db_client.http_client:
            await toxicity_db_client.connect()
        
        toxicity_scorer = ToxicityScorer(toxicity_db_client)
        logger.info("Toxicity scorer initialized")
    
    return toxicity_scorer
