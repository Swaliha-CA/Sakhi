"""
Correlation Analysis Service for Population Health Analytics

This service implements correlation analysis between EDC exposure and health outcomes,
environmental factors and health conditions, and generates predictive models for PPD risk.

Requirements: 15.2, 15.3
"""
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics
from datetime import datetime


class CorrelationAnalysisService:
    """Service for analyzing correlations in population health data"""
    
    def __init__(self, min_sample_size: int = 30):
        """
        Initialize correlation analysis service
        
        Args:
            min_sample_size: Minimum sample size for statistical significance (default: 30)
        """
        self.min_sample_size = min_sample_size
    
    def analyze_edc_pcos_correlation(
        self,
        anonymized_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Identify correlations between specific EDCs and PCOS prevalence
        
        Args:
            anonymized_data: List of anonymized user records with EDC exposure and PCOS status
            
        Returns:
            Dictionary containing correlation analysis results
        """
        # Group users by PCOS status
        pcos_users = []
        non_pcos_users = []
        
        for record in anonymized_data:
            conditions = record.get('conditions', [])
            has_pcos = any(
                c.get('name', '').lower() == 'pcos' 
                for c in conditions if isinstance(c, dict)
            )
            
            if has_pcos:
                pcos_users.append(record)
            else:
                non_pcos_users.append(record)
        
        # Calculate EDC exposure statistics for each group
        edc_types = ['bpa', 'phthalate', 'paraben', 'organochlorine', 'heavy_metal', 'pfas']
        correlations = {}
        
        for edc_type in edc_types:
            pcos_exposures = self._extract_edc_exposures(pcos_users, edc_type)
            non_pcos_exposures = self._extract_edc_exposures(non_pcos_users, edc_type)
            
            if len(pcos_exposures) >= self.min_sample_size and len(non_pcos_exposures) >= self.min_sample_size:
                # Calculate statistics
                pcos_mean = statistics.mean(pcos_exposures) if pcos_exposures else 0
                non_pcos_mean = statistics.mean(non_pcos_exposures) if non_pcos_exposures else 0
                
                pcos_stdev = statistics.stdev(pcos_exposures) if len(pcos_exposures) > 1 else 0
                non_pcos_stdev = statistics.stdev(non_pcos_exposures) if len(non_pcos_exposures) > 1 else 0
                
                # Calculate effect size (Cohen's d)
                pooled_stdev = self._calculate_pooled_stdev(
                    pcos_exposures, non_pcos_exposures, pcos_stdev, non_pcos_stdev
                )
                effect_size = (pcos_mean - non_pcos_mean) / pooled_stdev if pooled_stdev > 0 else 0
                
                # Determine correlation strength
                correlation_strength = self._interpret_effect_size(effect_size)
                
                correlations[edc_type] = {
                    'pcos_group': {
                        'mean_exposure': pcos_mean,
                        'stdev': pcos_stdev,
                        'sample_size': len(pcos_exposures)
                    },
                    'non_pcos_group': {
                        'mean_exposure': non_pcos_mean,
                        'stdev': non_pcos_stdev,
                        'sample_size': len(non_pcos_exposures)
                    },
                    'effect_size': effect_size,
                    'correlation_strength': correlation_strength,
                    'statistically_significant': abs(effect_size) > 0.2  # Small effect threshold
                }
        
        return {
            'edc_pcos_correlations': correlations,
            'pcos_prevalence': len(pcos_users) / len(anonymized_data) if anonymized_data else 0,
            'total_users': len(anonymized_data),
            'pcos_users': len(pcos_users),
            'non_pcos_users': len(non_pcos_users),
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def analyze_environmental_health_outcomes(
        self,
        anonymized_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze correlations between environmental factors and health outcomes
        
        Args:
            anonymized_data: List of anonymized user records with environmental and health data
            
        Returns:
            Dictionary containing environmental correlation analysis
        """
        # Analyze heat exposure and health outcomes
        heat_analysis = self._analyze_heat_exposure_outcomes(anonymized_data)
        
        # Analyze regional patterns
        regional_analysis = self._analyze_regional_health_patterns(anonymized_data)
        
        # Analyze occupational factors
        occupational_analysis = self._analyze_occupational_health_patterns(anonymized_data)
        
        return {
            'heat_exposure_analysis': heat_analysis,
            'regional_patterns': regional_analysis,
            'occupational_patterns': occupational_analysis,
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def generate_ppd_risk_model(
        self,
        anonymized_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate predictive model for PPD risk based on population data
        
        Args:
            anonymized_data: List of anonymized user records with PPD outcomes and risk factors
            
        Returns:
            Dictionary containing PPD risk model parameters and validation metrics
        """
        # Filter for postpartum users with PPD outcome data
        postpartum_users = [
            record for record in anonymized_data
            if record.get('reproductive_stage') == 'postpartum'
        ]
        
        if len(postpartum_users) < self.min_sample_size:
            return {
                'error': 'Insufficient data for PPD risk modeling',
                'required_samples': self.min_sample_size,
                'available_samples': len(postpartum_users)
            }
        
        # Identify PPD cases
        ppd_users = []
        non_ppd_users = []
        
        for record in postpartum_users:
            conditions = record.get('conditions', [])
            has_ppd = any(
                'ppd' in c.get('name', '').lower() or 'postpartum depression' in c.get('name', '').lower()
                for c in conditions if isinstance(c, dict)
            )
            
            if has_ppd:
                ppd_users.append(record)
            else:
                non_ppd_users.append(record)
        
        # Analyze risk factors
        risk_factors = self._analyze_ppd_risk_factors(ppd_users, non_ppd_users)
        
        # Calculate model parameters
        model_params = self._calculate_ppd_model_parameters(risk_factors)
        
        # Validate model
        validation_metrics = self._validate_ppd_model(ppd_users, non_ppd_users, model_params)
        
        return {
            'model_parameters': model_params,
            'risk_factors': risk_factors,
            'validation_metrics': validation_metrics,
            'ppd_prevalence': len(ppd_users) / len(postpartum_users) if postpartum_users else 0,
            'total_postpartum_users': len(postpartum_users),
            'ppd_cases': len(ppd_users),
            'non_ppd_cases': len(non_ppd_users),
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def _extract_edc_exposures(
        self,
        records: List[Dict[str, Any]],
        edc_type: str
    ) -> List[float]:
        """Extract EDC exposure values for a specific EDC type"""
        exposures = []
        
        for record in records:
            # Check for exposure data in various formats
            exposure_log = record.get('exposure_log', {})
            
            if isinstance(exposure_log, dict):
                exposure_by_type = exposure_log.get('exposure_by_type', {})
                if edc_type in exposure_by_type:
                    exposures.append(float(exposure_by_type[edc_type]))
            
            # Also check for product scan data
            product_scans = record.get('product_scans', [])
            if isinstance(product_scans, list):
                for scan in product_scans:
                    if isinstance(scan, dict):
                        toxicity_score = scan.get('toxicity_score', {})
                        if isinstance(toxicity_score, dict):
                            flagged_chemicals = toxicity_score.get('flagged_chemicals', [])
                            for chemical in flagged_chemicals:
                                if isinstance(chemical, dict) and edc_type in chemical.get('edc_type', []):
                                    risk_score = chemical.get('risk_score', 0)
                                    exposures.append(float(risk_score))
        
        return exposures
    
    def _calculate_pooled_stdev(
        self,
        group1: List[float],
        group2: List[float],
        stdev1: float,
        stdev2: float
    ) -> float:
        """Calculate pooled standard deviation for two groups"""
        n1 = len(group1)
        n2 = len(group2)
        
        if n1 + n2 <= 2:
            return 0
        
        pooled_variance = ((n1 - 1) * stdev1**2 + (n2 - 1) * stdev2**2) / (n1 + n2 - 2)
        return pooled_variance ** 0.5
    
    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_effect = abs(effect_size)
        
        if abs_effect < 0.2:
            return "negligible"
        elif abs_effect < 0.5:
            return "small"
        elif abs_effect < 0.8:
            return "medium"
        else:
            return "large"
    
    def _analyze_heat_exposure_outcomes(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze correlation between heat exposure and health outcomes"""
        high_heat_users = []
        low_heat_users = []
        
        for record in records:
            heat_exposure = record.get('cumulative_heat_exposure', 0)
            
            # Threshold for high heat exposure (can be adjusted)
            if heat_exposure > 100:  # Arbitrary threshold
                high_heat_users.append(record)
            else:
                low_heat_users.append(record)
        
        # Analyze health outcomes in each group
        high_heat_outcomes = self._extract_health_outcomes(high_heat_users)
        low_heat_outcomes = self._extract_health_outcomes(low_heat_users)
        
        return {
            'high_heat_group': {
                'sample_size': len(high_heat_users),
                'health_outcomes': high_heat_outcomes
            },
            'low_heat_group': {
                'sample_size': len(low_heat_users),
                'health_outcomes': low_heat_outcomes
            },
            'correlation_detected': len(high_heat_users) >= self.min_sample_size and len(low_heat_users) >= self.min_sample_size
        }
    
    def _analyze_regional_health_patterns(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze health patterns by region"""
        regional_data = defaultdict(list)
        
        for record in records:
            region = record.get('region', 'unknown')
            regional_data[region].append(record)
        
        regional_patterns = {}
        for region, region_records in regional_data.items():
            if len(region_records) >= self.min_sample_size:
                regional_patterns[region] = {
                    'sample_size': len(region_records),
                    'health_outcomes': self._extract_health_outcomes(region_records),
                    'average_edc_exposure': self._calculate_average_edc_exposure(region_records)
                }
        
        return regional_patterns
    
    def _analyze_occupational_health_patterns(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze health patterns by occupation"""
        occupational_data = defaultdict(list)
        
        for record in records:
            occupation = record.get('occupation', 'unknown')
            occupational_data[occupation].append(record)
        
        occupational_patterns = {}
        for occupation, occ_records in occupational_data.items():
            if len(occ_records) >= self.min_sample_size:
                occupational_patterns[occupation] = {
                    'sample_size': len(occ_records),
                    'health_outcomes': self._extract_health_outcomes(occ_records),
                    'average_heat_exposure': self._calculate_average_heat_exposure(occ_records)
                }
        
        return occupational_patterns
    
    def _extract_health_outcomes(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract health outcome statistics from records"""
        conditions_count = defaultdict(int)
        total_records = len(records)
        
        for record in records:
            conditions = record.get('conditions', [])
            for condition in conditions:
                if isinstance(condition, dict):
                    condition_name = condition.get('name', '').lower()
                    conditions_count[condition_name] += 1
        
        # Calculate prevalence rates
        prevalence = {
            condition: count / total_records if total_records > 0 else 0
            for condition, count in conditions_count.items()
        }
        
        return {
            'condition_counts': dict(conditions_count),
            'prevalence_rates': prevalence,
            'total_records': total_records
        }
    
    def _calculate_average_edc_exposure(
        self,
        records: List[Dict[str, Any]]
    ) -> float:
        """Calculate average EDC exposure across records"""
        exposures = []
        
        for record in records:
            exposure_log = record.get('exposure_log', {})
            if isinstance(exposure_log, dict):
                total_exposure = exposure_log.get('total_exposure', 0)
                if total_exposure > 0:
                    exposures.append(total_exposure)
        
        return statistics.mean(exposures) if exposures else 0
    
    def _calculate_average_heat_exposure(
        self,
        records: List[Dict[str, Any]]
    ) -> float:
        """Calculate average heat exposure across records"""
        exposures = []
        
        for record in records:
            heat_exposure = record.get('cumulative_heat_exposure', 0)
            if heat_exposure > 0:
                exposures.append(heat_exposure)
        
        return statistics.mean(exposures) if exposures else 0
    
    def _analyze_ppd_risk_factors(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze risk factors for PPD"""
        risk_factors = {}
        
        # Analyze EPDS/PHQ-9 scores
        risk_factors['mood_scores'] = self._compare_mood_scores(ppd_users, non_ppd_users)
        
        # Analyze phthalate exposure
        risk_factors['phthalate_exposure'] = self._compare_phthalate_exposure(ppd_users, non_ppd_users)
        
        # Analyze progesterone levels
        risk_factors['progesterone_levels'] = self._compare_progesterone_levels(ppd_users, non_ppd_users)
        
        # Analyze micronutrient status
        risk_factors['micronutrient_status'] = self._compare_micronutrient_status(ppd_users, non_ppd_users)
        
        # Analyze social support
        risk_factors['social_support'] = self._compare_social_support(ppd_users, non_ppd_users)
        
        return risk_factors
    
    def _compare_mood_scores(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare mood screening scores between groups"""
        ppd_scores = self._extract_mood_scores(ppd_users)
        non_ppd_scores = self._extract_mood_scores(non_ppd_users)
        
        return {
            'ppd_group_mean': statistics.mean(ppd_scores) if ppd_scores else 0,
            'non_ppd_group_mean': statistics.mean(non_ppd_scores) if non_ppd_scores else 0,
            'difference': (statistics.mean(ppd_scores) - statistics.mean(non_ppd_scores)) if ppd_scores and non_ppd_scores else 0
        }
    
    def _compare_phthalate_exposure(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare phthalate exposure between groups"""
        ppd_exposures = self._extract_edc_exposures(ppd_users, 'phthalate')
        non_ppd_exposures = self._extract_edc_exposures(non_ppd_users, 'phthalate')
        
        return {
            'ppd_group_mean': statistics.mean(ppd_exposures) if ppd_exposures else 0,
            'non_ppd_group_mean': statistics.mean(non_ppd_exposures) if non_ppd_exposures else 0,
            'difference': (statistics.mean(ppd_exposures) - statistics.mean(non_ppd_exposures)) if ppd_exposures and non_ppd_exposures else 0
        }
    
    def _compare_progesterone_levels(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare progesterone levels between groups"""
        ppd_levels = self._extract_progesterone_levels(ppd_users)
        non_ppd_levels = self._extract_progesterone_levels(non_ppd_users)
        
        return {
            'ppd_group_mean': statistics.mean(ppd_levels) if ppd_levels else 0,
            'non_ppd_group_mean': statistics.mean(non_ppd_levels) if non_ppd_levels else 0,
            'difference': (statistics.mean(ppd_levels) - statistics.mean(non_ppd_levels)) if ppd_levels and non_ppd_levels else 0
        }
    
    def _compare_micronutrient_status(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare micronutrient status between groups"""
        ppd_deficiencies = self._count_micronutrient_deficiencies(ppd_users)
        non_ppd_deficiencies = self._count_micronutrient_deficiencies(non_ppd_users)
        
        return {
            'ppd_group_deficiency_rate': ppd_deficiencies / len(ppd_users) if ppd_users else 0,
            'non_ppd_group_deficiency_rate': non_ppd_deficiencies / len(non_ppd_users) if non_ppd_users else 0
        }
    
    def _compare_social_support(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare social support levels between groups"""
        ppd_support = self._extract_social_support_scores(ppd_users)
        non_ppd_support = self._extract_social_support_scores(non_ppd_users)
        
        return {
            'ppd_group_mean': statistics.mean(ppd_support) if ppd_support else 0,
            'non_ppd_group_mean': statistics.mean(non_ppd_support) if non_ppd_support else 0,
            'difference': (statistics.mean(ppd_support) - statistics.mean(non_ppd_support)) if ppd_support and non_ppd_support else 0
        }
    
    def _extract_mood_scores(self, records: List[Dict[str, Any]]) -> List[float]:
        """Extract mood screening scores from records"""
        scores = []
        for record in records:
            # Check for EPDS or PHQ-9 scores
            if 'epds_score' in record:
                scores.append(float(record['epds_score']))
            elif 'phq9_score' in record:
                scores.append(float(record['phq9_score']))
            elif 'total_score' in record:
                scores.append(float(record['total_score']))
        return scores
    
    def _extract_progesterone_levels(self, records: List[Dict[str, Any]]) -> List[float]:
        """Extract progesterone levels from records"""
        levels = []
        for record in records:
            if 'progesterone_level' in record:
                levels.append(float(record['progesterone_level']))
        return levels
    
    def _count_micronutrient_deficiencies(self, records: List[Dict[str, Any]]) -> int:
        """Count users with micronutrient deficiencies"""
        deficiency_count = 0
        for record in records:
            # Check for deficiency flags
            if record.get('iron_deficient') or record.get('b12_deficient') or record.get('folate_deficient'):
                deficiency_count += 1
        return deficiency_count
    
    def _extract_social_support_scores(self, records: List[Dict[str, Any]]) -> List[float]:
        """Extract social support scores from records"""
        scores = []
        for record in records:
            if 'social_support_score' in record:
                scores.append(float(record['social_support_score']))
        return scores
    
    def _calculate_ppd_model_parameters(
        self,
        risk_factors: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate PPD risk model parameters based on risk factor analysis"""
        # Define feature weights based on research (from design doc)
        weights = {
            'mood_scores': 0.30,  # EPDS/PHQ-9 (30%)
            'progesterone_levels': 0.25,  # Hormonal factors (25%)
            'phthalate_exposure': 0.20,  # Environmental exposure (20%)
            'micronutrient_status': 0.15,  # Micronutrients (15%)
            'social_support': 0.10  # Social factors (10%)
        }
        
        # Calculate thresholds based on risk factor differences
        thresholds = {}
        for factor, weight in weights.items():
            if factor in risk_factors:
                factor_data = risk_factors[factor]
                if 'difference' in factor_data:
                    # Use the difference to set threshold
                    thresholds[factor] = {
                        'weight': weight,
                        'threshold_difference': factor_data['difference']
                    }
        
        return {
            'feature_weights': weights,
            'risk_thresholds': thresholds,
            'high_risk_threshold': 70,  # Score >70 triggers ASHA alert
            'model_type': 'weighted_risk_score'
        }
    
    def _validate_ppd_model(
        self,
        ppd_users: List[Dict[str, Any]],
        non_ppd_users: List[Dict[str, Any]],
        model_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate PPD risk model performance"""
        # Simple validation: calculate how well the model would classify users
        weights = model_params['feature_weights']
        
        # Calculate risk scores for all users
        ppd_risk_scores = [self._calculate_risk_score(user, weights) for user in ppd_users]
        non_ppd_risk_scores = [self._calculate_risk_score(user, weights) for user in non_ppd_users]
        
        # Count correct classifications (using threshold of 70)
        threshold = model_params['high_risk_threshold']
        true_positives = sum(1 for score in ppd_risk_scores if score >= threshold)
        false_negatives = sum(1 for score in ppd_risk_scores if score < threshold)
        true_negatives = sum(1 for score in non_ppd_risk_scores if score < threshold)
        false_positives = sum(1 for score in non_ppd_risk_scores if score >= threshold)
        
        # Calculate metrics
        total = len(ppd_users) + len(non_ppd_users)
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0
        sensitivity = true_positives / len(ppd_users) if ppd_users else 0
        specificity = true_negatives / len(non_ppd_users) if non_ppd_users else 0
        
        return {
            'accuracy': accuracy,
            'sensitivity': sensitivity,
            'specificity': specificity,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'true_negatives': true_negatives,
            'false_negatives': false_negatives
        }
    
    def _calculate_risk_score(
        self,
        user: Dict[str, Any],
        weights: Dict[str, float]
    ) -> float:
        """Calculate PPD risk score for a user"""
        score = 0
        
        # Mood scores (higher = higher risk)
        mood_score = user.get('epds_score', user.get('phq9_score', user.get('total_score', 0)))
        score += (mood_score / 27) * 100 * weights.get('mood_scores', 0)  # Normalize to 0-100
        
        # Phthalate exposure (higher = higher risk)
        phthalate_exposures = self._extract_edc_exposures([user], 'phthalate')
        if phthalate_exposures:
            phthalate_score = min(phthalate_exposures[0] / 100, 1) * 100  # Normalize
            score += phthalate_score * weights.get('phthalate_exposure', 0)
        
        # Progesterone (lower = higher risk, so invert)
        progesterone = user.get('progesterone_level', 50)  # Default mid-range
        progesterone_score = (100 - min(progesterone, 100))  # Invert so low = high risk
        score += progesterone_score * weights.get('progesterone_levels', 0)
        
        # Micronutrient deficiency (deficient = higher risk)
        has_deficiency = user.get('iron_deficient') or user.get('b12_deficient') or user.get('folate_deficient')
        micronutrient_score = 100 if has_deficiency else 0
        score += micronutrient_score * weights.get('micronutrient_status', 0)
        
        # Social support (lower = higher risk, so invert)
        social_support = user.get('social_support_score', 50)  # Default mid-range
        social_score = (100 - min(social_support, 100))  # Invert
        score += social_score * weights.get('social_support', 0)
        
        return score
