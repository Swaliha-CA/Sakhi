"""
Data Anonymization Service for Public Health Analytics

This service implements PII scrubbing, demographic aggregation, and k-anonymity
to enable population-level health analytics while protecting user privacy.

Requirements: 15.1
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import hashlib


class AnonymizationService:
    """Service for anonymizing health data for public health research"""
    
    def __init__(self, k_anonymity_threshold: int = 5):
        """
        Initialize anonymization service
        
        Args:
            k_anonymity_threshold: Minimum group size for reporting (default: 5)
        """
        self.k_anonymity_threshold = k_anonymity_threshold
    
    def scrub_pii(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove personally identifiable information from user data
        
        Args:
            user_data: Raw user data dictionary
            
        Returns:
            Anonymized user data with PII removed
        """
        # Create a copy to avoid modifying original
        anonymized = user_data.copy()
        
        # Remove direct identifiers
        pii_fields = [
            'name', 'phone_number', 'abha_id', 'email', 
            'address', 'device_id', 'current_device_id'
        ]
        
        for field in pii_fields:
            if field in anonymized:
                del anonymized[field]
        
        # Generate pseudonymous ID (one-way hash)
        if 'id' in user_data or 'user_id' in user_data:
            original_id = str(user_data.get('id') or user_data.get('user_id'))
            anonymized['pseudonym_id'] = self._generate_pseudonym(original_id)
            
            # Remove original ID
            if 'id' in anonymized:
                del anonymized['id']
            if 'user_id' in anonymized:
                del anonymized['user_id']
        
        return anonymized
    
    def _generate_pseudonym(self, identifier: str) -> str:
        """
        Generate a one-way pseudonymous identifier
        
        Args:
            identifier: Original identifier
            
        Returns:
            SHA-256 hash of the identifier
        """
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def aggregate_by_demographics(
        self, 
        user_records: List[Dict[str, Any]],
        group_by: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Aggregate user data by demographic groups
        
        Args:
            user_records: List of anonymized user records
            group_by: List of fields to group by (default: age_group, region, condition)
            
        Returns:
            Dictionary mapping demographic keys to lists of records
        """
        if group_by is None:
            group_by = ['age_group', 'region']
        
        # First, categorize continuous variables
        categorized_records = []
        for record in user_records:
            categorized = record.copy()
            
            # Categorize age into groups
            if 'age' in record:
                categorized['age_group'] = self._categorize_age(record['age'])
            
            # Standardize region if present
            if 'state' in record:
                categorized['region'] = self._categorize_region(record['state'])
            elif 'district' in record:
                # Use district as region if state not available
                categorized['region'] = record['district']
            
            categorized_records.append(categorized)
        
        # Group records by specified fields
        groups = defaultdict(list)
        for record in categorized_records:
            # Create group key from specified fields
            key_parts = []
            for field in group_by:
                value = record.get(field, 'unknown')
                key_parts.append(f"{field}:{value}")
            
            group_key = "|".join(key_parts)
            groups[group_key].append(record)
        
        return dict(groups)
    
    def _categorize_age(self, age: int) -> str:
        """
        Categorize age into groups for anonymization
        
        Args:
            age: Age in years
            
        Returns:
            Age group string
        """
        if age < 18:
            return "under_18"
        elif age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55_plus"
    
    def _categorize_region(self, state: str) -> str:
        """
        Categorize Indian states into broader regions
        
        Args:
            state: State name
            
        Returns:
            Region name (North, South, East, West, Central, Northeast)
        """
        # Regional mapping for Indian states
        region_map = {
            # North
            'punjab': 'north', 'haryana': 'north', 'himachal pradesh': 'north',
            'jammu and kashmir': 'north', 'ladakh': 'north', 'delhi': 'north',
            'uttarakhand': 'north', 'uttar pradesh': 'north', 'rajasthan': 'north',
            
            # South
            'karnataka': 'south', 'tamil nadu': 'south', 'kerala': 'south',
            'andhra pradesh': 'south', 'telangana': 'south', 'puducherry': 'south',
            
            # East
            'west bengal': 'east', 'odisha': 'east', 'bihar': 'east',
            'jharkhand': 'east',
            
            # West
            'maharashtra': 'west', 'gujarat': 'west', 'goa': 'west',
            'daman and diu': 'west', 'dadra and nagar haveli': 'west',
            
            # Central
            'madhya pradesh': 'central', 'chhattisgarh': 'central',
            
            # Northeast
            'assam': 'northeast', 'meghalaya': 'northeast', 'manipur': 'northeast',
            'mizoram': 'northeast', 'nagaland': 'northeast', 'tripura': 'northeast',
            'arunachal pradesh': 'northeast', 'sikkim': 'northeast'
        }
        
        state_lower = state.lower() if state else ''
        return region_map.get(state_lower, 'unknown')
    
    def ensure_k_anonymity(
        self, 
        grouped_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ensure k-anonymity by filtering out groups smaller than threshold
        
        Args:
            grouped_data: Dictionary of demographic groups
            
        Returns:
            Filtered dictionary with only groups meeting k-anonymity threshold
        """
        filtered_groups = {}
        
        for group_key, records in grouped_data.items():
            if len(records) >= self.k_anonymity_threshold:
                filtered_groups[group_key] = records
        
        return filtered_groups
    
    def aggregate_health_metrics(
        self,
        grouped_data: Dict[str, List[Dict[str, Any]]],
        metrics: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate aggregate statistics for each demographic group
        
        Args:
            grouped_data: Dictionary of demographic groups
            metrics: List of metric fields to aggregate
            
        Returns:
            Dictionary mapping group keys to aggregate statistics
        """
        if metrics is None:
            metrics = [
                'overall_score', 'hormonal_health_score', 
                'total_score', 'risk_level'
            ]
        
        aggregates = {}
        
        for group_key, records in grouped_data.items():
            group_stats = {
                'count': len(records),
                'demographics': self._parse_group_key(group_key)
            }
            
            # Calculate statistics for each metric
            for metric in metrics:
                values = [r.get(metric) for r in records if metric in r and r.get(metric) is not None]
                
                if values:
                    if isinstance(values[0], (int, float)):
                        # Numeric metrics: calculate mean, min, max
                        group_stats[metric] = {
                            'mean': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values),
                            'count': len(values)
                        }
                    else:
                        # Categorical metrics: calculate distribution
                        distribution = defaultdict(int)
                        for value in values:
                            distribution[str(value)] += 1
                        group_stats[metric] = dict(distribution)
            
            aggregates[group_key] = group_stats
        
        return aggregates
    
    def _parse_group_key(self, group_key: str) -> Dict[str, str]:
        """
        Parse group key back into demographic fields
        
        Args:
            group_key: Pipe-separated group key
            
        Returns:
            Dictionary of demographic fields
        """
        demographics = {}
        parts = group_key.split('|')
        
        for part in parts:
            if ':' in part:
                field, value = part.split(':', 1)
                demographics[field] = value
        
        return demographics
    
    def anonymize_and_aggregate(
        self,
        user_records: List[Dict[str, Any]],
        group_by: List[str] = None,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """
        Complete anonymization pipeline: scrub PII, aggregate, ensure k-anonymity
        
        Args:
            user_records: List of raw user records
            group_by: Fields to group by
            metrics: Metrics to aggregate
            
        Returns:
            Anonymized aggregate statistics
        """
        # Step 1: Scrub PII from all records
        anonymized_records = [self.scrub_pii(record) for record in user_records]
        
        # Step 2: Aggregate by demographics
        grouped_data = self.aggregate_by_demographics(anonymized_records, group_by)
        
        # Step 3: Ensure k-anonymity
        k_anonymous_groups = self.ensure_k_anonymity(grouped_data)
        
        # Step 4: Calculate aggregate statistics
        aggregates = self.aggregate_health_metrics(k_anonymous_groups, metrics)
        
        # Add metadata
        result = {
            'aggregates': aggregates,
            'metadata': {
                'total_records': len(user_records),
                'anonymized_records': len(anonymized_records),
                'groups_before_k_anonymity': len(grouped_data),
                'groups_after_k_anonymity': len(k_anonymous_groups),
                'k_threshold': self.k_anonymity_threshold,
                'generated_at': datetime.utcnow().isoformat()
            }
        }
        
        return result
