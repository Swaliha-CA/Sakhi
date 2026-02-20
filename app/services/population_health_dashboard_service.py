"""
Population Health Dashboard Service

This service provides dashboards and reporting interfaces for public health authorities
to view aggregated and analyzed health data, detect risk patterns, and generate reports.

Requirements: 15.4, 15.5
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.anonymization_service import AnonymizationService
from app.services.correlation_analysis_service import CorrelationAnalysisService


class PopulationHealthDashboardService:
    """Service for population health dashboards and reporting"""
    
    def __init__(
        self,
        anonymization_service: Optional[AnonymizationService] = None,
        correlation_service: Optional[CorrelationAnalysisService] = None
    ):
        """
        Initialize population health dashboard service
        
        Args:
            anonymization_service: Service for data anonymization
            correlation_service: Service for correlation analysis
        """
        self.anonymization_service = anonymization_service or AnonymizationService()
        self.correlation_service = correlation_service or CorrelationAnalysisService()
        
        # Risk pattern thresholds
        self.risk_thresholds = {
            'edc_exposure_high': 75,  # High EDC exposure threshold
            'pcos_prevalence_high': 0.15,  # 15% prevalence threshold
            'ppd_prevalence_high': 0.25,  # 25% prevalence threshold
            'anemia_prevalence_high': 0.40,  # 40% prevalence threshold
            'heat_exposure_high': 150,  # High heat exposure threshold
        }
    
    def get_aggregate_metrics(
        self,
        user_records: List[Dict[str, Any]],
        group_by: List[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate health metrics for population health dashboard
        
        Args:
            user_records: List of raw user records
            group_by: Fields to group by (default: age_group, region)
            time_range: Optional time range filter (start_date, end_date)
            
        Returns:
            Dictionary containing aggregate metrics
        """
        # Filter by time range if provided
        if time_range:
            user_records = self._filter_by_time_range(user_records, time_range)
        
        # Anonymize and aggregate data
        anonymized_data = self.anonymization_service.anonymize_and_aggregate(
            user_records,
            group_by=group_by or ['age_group', 'region'],
            metrics=['overall_score', 'hormonal_health_score', 'total_score', 'risk_level']
        )
        
        # Calculate additional population-level metrics
        population_metrics = self._calculate_population_metrics(user_records)
        
        # Combine results
        return {
            'aggregate_data': anonymized_data['aggregates'],
            'population_metrics': population_metrics,
            'metadata': anonymized_data['metadata'],
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def get_edc_exposure_patterns(
        self,
        user_records: List[Dict[str, Any]],
        group_by: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get EDC exposure patterns across demographics
        
        Args:
            user_records: List of raw user records
            group_by: Fields to group by
            
        Returns:
            Dictionary containing EDC exposure patterns
        """
        # Anonymize data
        anonymized_records = [
            self.anonymization_service.scrub_pii(record) 
            for record in user_records
        ]
        
        # Group by demographics
        grouped_data = self.anonymization_service.aggregate_by_demographics(
            anonymized_records,
            group_by=group_by or ['age_group', 'region']
        )
        
        # Ensure k-anonymity
        k_anonymous_groups = self.anonymization_service.ensure_k_anonymity(grouped_data)
        
        # Calculate EDC exposure patterns for each group
        exposure_patterns = {}
        for group_key, records in k_anonymous_groups.items():
            exposure_patterns[group_key] = self._calculate_edc_patterns(records)
        
        return {
            'exposure_patterns': exposure_patterns,
            'total_groups': len(exposure_patterns),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def get_condition_prevalence(
        self,
        user_records: List[Dict[str, Any]],
        conditions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get prevalence rates for specific health conditions
        
        Args:
            user_records: List of raw user records
            conditions: List of conditions to analyze (default: PCOS, PPD, anemia)
            
        Returns:
            Dictionary containing prevalence rates by demographics
        """
        if conditions is None:
            conditions = ['pcos', 'ppd', 'postpartum depression', 'anemia']
        
        # Anonymize data
        anonymized_records = [
            self.anonymization_service.scrub_pii(record) 
            for record in user_records
        ]
        
        # Group by demographics
        grouped_data = self.anonymization_service.aggregate_by_demographics(
            anonymized_records,
            group_by=['age_group', 'region']
        )
        
        # Ensure k-anonymity
        k_anonymous_groups = self.anonymization_service.ensure_k_anonymity(grouped_data)
        
        # Calculate prevalence for each group
        prevalence_data = {}
        for group_key, records in k_anonymous_groups.items():
            prevalence_data[group_key] = self._calculate_condition_prevalence(
                records, 
                conditions
            )
        
        # Calculate overall prevalence
        overall_prevalence = self._calculate_condition_prevalence(
            anonymized_records,
            conditions
        )
        
        return {
            'prevalence_by_group': prevalence_data,
            'overall_prevalence': overall_prevalence,
            'total_users': len(user_records),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def detect_risk_patterns(
        self,
        user_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect emerging risk patterns in population health data
        
        Args:
            user_records: List of raw user records
            
        Returns:
            Dictionary containing detected risk patterns and alerts
        """
        # Anonymize data
        anonymized_records = [
            self.anonymization_service.scrub_pii(record) 
            for record in user_records
        ]
        
        # Run correlation analyses
        edc_pcos_analysis = self.correlation_service.analyze_edc_pcos_correlation(
            anonymized_records
        )
        
        environmental_analysis = self.correlation_service.analyze_environmental_health_outcomes(
            anonymized_records
        )
        
        ppd_model = self.correlation_service.generate_ppd_risk_model(
            anonymized_records
        )
        
        # Detect risk patterns
        risk_patterns = []
        
        # Check EDC-PCOS correlations
        for edc_type, correlation in edc_pcos_analysis.get('edc_pcos_correlations', {}).items():
            if correlation.get('statistically_significant'):
                risk_patterns.append({
                    'type': 'edc_pcos_correlation',
                    'edc_type': edc_type,
                    'effect_size': correlation['effect_size'],
                    'correlation_strength': correlation['correlation_strength'],
                    'severity': self._determine_severity(correlation['effect_size']),
                    'description': f"Significant correlation detected between {edc_type} exposure and PCOS prevalence"
                })
        
        # Check PCOS prevalence
        pcos_prevalence = edc_pcos_analysis.get('pcos_prevalence', 0)
        if pcos_prevalence > self.risk_thresholds['pcos_prevalence_high']:
            risk_patterns.append({
                'type': 'high_pcos_prevalence',
                'prevalence': pcos_prevalence,
                'threshold': self.risk_thresholds['pcos_prevalence_high'],
                'severity': 'high',
                'description': f"PCOS prevalence ({pcos_prevalence:.1%}) exceeds threshold ({self.risk_thresholds['pcos_prevalence_high']:.1%})"
            })
        
        # Check PPD prevalence
        if 'ppd_prevalence' in ppd_model:
            ppd_prevalence = ppd_model['ppd_prevalence']
            if ppd_prevalence > self.risk_thresholds['ppd_prevalence_high']:
                risk_patterns.append({
                    'type': 'high_ppd_prevalence',
                    'prevalence': ppd_prevalence,
                    'threshold': self.risk_thresholds['ppd_prevalence_high'],
                    'severity': 'high',
                    'description': f"PPD prevalence ({ppd_prevalence:.1%}) exceeds threshold ({self.risk_thresholds['ppd_prevalence_high']:.1%})"
                })
        
        # Check regional patterns
        regional_patterns = environmental_analysis.get('regional_patterns', {})
        for region, data in regional_patterns.items():
            # Check for high EDC exposure in region
            avg_edc = data.get('average_edc_exposure', 0)
            if avg_edc > self.risk_thresholds['edc_exposure_high']:
                risk_patterns.append({
                    'type': 'regional_high_edc',
                    'region': region,
                    'average_exposure': avg_edc,
                    'threshold': self.risk_thresholds['edc_exposure_high'],
                    'severity': 'medium',
                    'description': f"High EDC exposure detected in {region} region"
                })
        
        # Check occupational patterns
        occupational_patterns = environmental_analysis.get('occupational_patterns', {})
        for occupation, data in occupational_patterns.items():
            # Check for high heat exposure
            avg_heat = data.get('average_heat_exposure', 0)
            if avg_heat > self.risk_thresholds['heat_exposure_high']:
                risk_patterns.append({
                    'type': 'occupational_heat_risk',
                    'occupation': occupation,
                    'average_exposure': avg_heat,
                    'threshold': self.risk_thresholds['heat_exposure_high'],
                    'severity': 'medium',
                    'description': f"High heat exposure detected for {occupation} workers"
                })
        
        return {
            'risk_patterns': risk_patterns,
            'total_patterns_detected': len(risk_patterns),
            'edc_pcos_analysis': edc_pcos_analysis,
            'environmental_analysis': environmental_analysis,
            'ppd_model': ppd_model,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def generate_health_authority_report(
        self,
        user_records: List[Dict[str, Any]],
        report_type: str = 'comprehensive',
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive report for health authorities
        
        Args:
            user_records: List of raw user records
            report_type: Type of report (comprehensive, summary, trends)
            time_range: Optional time range for the report
            
        Returns:
            Dictionary containing the generated report
        """
        # Filter by time range if provided
        if time_range:
            user_records = self._filter_by_time_range(user_records, time_range)
        
        # Get all dashboard data
        aggregate_metrics = self.get_aggregate_metrics(user_records)
        edc_patterns = self.get_edc_exposure_patterns(user_records)
        prevalence_data = self.get_condition_prevalence(user_records)
        risk_patterns = self.detect_risk_patterns(user_records)
        
        # Build report based on type
        if report_type == 'summary':
            report = self._generate_summary_report(
                aggregate_metrics,
                prevalence_data,
                risk_patterns
            )
        elif report_type == 'trends':
            report = self._generate_trends_report(
                user_records,
                time_range
            )
        else:  # comprehensive
            report = {
                'report_type': 'comprehensive',
                'executive_summary': self._generate_executive_summary(
                    aggregate_metrics,
                    prevalence_data,
                    risk_patterns
                ),
                'aggregate_metrics': aggregate_metrics,
                'edc_exposure_patterns': edc_patterns,
                'condition_prevalence': prevalence_data,
                'risk_patterns': risk_patterns,
                'recommendations': self._generate_recommendations(risk_patterns)
            }
        
        # Add metadata
        report['metadata'] = {
            'report_id': self._generate_report_id(),
            'generated_at': datetime.utcnow().isoformat(),
            'time_range': time_range,
            'total_users': len(user_records),
            'report_type': report_type
        }
        
        return report
    
    def get_anemia_rates(
        self,
        user_records: List[Dict[str, Any]],
        group_by: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get anemia prevalence rates across demographics
        
        Args:
            user_records: List of raw user records
            group_by: Fields to group by
            
        Returns:
            Dictionary containing anemia rates
        """
        # Anonymize data
        anonymized_records = [
            self.anonymization_service.scrub_pii(record) 
            for record in user_records
        ]
        
        # Group by demographics
        grouped_data = self.anonymization_service.aggregate_by_demographics(
            anonymized_records,
            group_by=group_by or ['age_group', 'region', 'reproductive_stage']
        )
        
        # Ensure k-anonymity
        k_anonymous_groups = self.anonymization_service.ensure_k_anonymity(grouped_data)
        
        # Calculate anemia rates for each group
        anemia_rates = {}
        for group_key, records in k_anonymous_groups.items():
            anemia_count = 0
            total_count = len(records)
            
            for record in records:
                # Check for anemia condition
                conditions = record.get('conditions', [])
                has_anemia = any(
                    'anemia' in c.get('name', '').lower()
                    for c in conditions if isinstance(c, dict)
                )
                
                # Also check hemoglobin levels
                hemoglobin = record.get('hemoglobin_level')
                if hemoglobin and hemoglobin < 12.0:  # Anemia threshold for women
                    has_anemia = True
                
                if has_anemia:
                    anemia_count += 1
            
            anemia_rate = anemia_count / total_count if total_count > 0 else 0
            
            anemia_rates[group_key] = {
                'anemia_count': anemia_count,
                'total_count': total_count,
                'anemia_rate': anemia_rate,
                'severity': 'high' if anemia_rate > self.risk_thresholds['anemia_prevalence_high'] else 'normal',
                'demographics': self.anonymization_service._parse_group_key(group_key)
            }
        
        # Calculate overall anemia rate
        total_anemia = sum(data['anemia_count'] for data in anemia_rates.values())
        total_users = sum(data['total_count'] for data in anemia_rates.values())
        overall_rate = total_anemia / total_users if total_users > 0 else 0
        
        return {
            'anemia_rates_by_group': anemia_rates,
            'overall_anemia_rate': overall_rate,
            'total_users': total_users,
            'high_risk_groups': [
                group_key for group_key, data in anemia_rates.items()
                if data['severity'] == 'high'
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
    
    # Helper methods
    
    def _filter_by_time_range(
        self,
        records: List[Dict[str, Any]],
        time_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """Filter records by time range"""
        start_date = time_range.get('start_date')
        end_date = time_range.get('end_date')
        
        filtered = []
        for record in records:
            record_date = record.get('created_at') or record.get('updated_at')
            if isinstance(record_date, str):
                record_date = datetime.fromisoformat(record_date.replace('Z', '+00:00'))
            
            if record_date:
                if start_date and record_date < start_date:
                    continue
                if end_date and record_date > end_date:
                    continue
            
            filtered.append(record)
        
        return filtered
    
    def _calculate_population_metrics(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate population-level health metrics"""
        total_users = len(records)
        
        # Count conditions
        condition_counts = defaultdict(int)
        for record in records:
            conditions = record.get('conditions', [])
            for condition in conditions:
                if isinstance(condition, dict):
                    condition_name = condition.get('name', '').lower()
                    condition_counts[condition_name] += 1
        
        # Calculate average scores
        toxicity_scores = []
        hormonal_scores = []
        for record in records:
            if 'overall_score' in record:
                toxicity_scores.append(record['overall_score'])
            if 'hormonal_health_score' in record:
                hormonal_scores.append(record['hormonal_health_score'])
        
        avg_toxicity = sum(toxicity_scores) / len(toxicity_scores) if toxicity_scores else 0
        avg_hormonal = sum(hormonal_scores) / len(hormonal_scores) if hormonal_scores else 0
        
        return {
            'total_users': total_users,
            'condition_counts': dict(condition_counts),
            'average_toxicity_score': avg_toxicity,
            'average_hormonal_score': avg_hormonal,
            'pcos_count': condition_counts.get('pcos', 0),
            'ppd_count': condition_counts.get('ppd', 0) + condition_counts.get('postpartum depression', 0),
            'anemia_count': condition_counts.get('anemia', 0)
        }
    
    def _calculate_edc_patterns(
        self,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate EDC exposure patterns for a group"""
        edc_types = ['bpa', 'phthalate', 'paraben', 'organochlorine', 'heavy_metal', 'pfas']
        edc_exposures = defaultdict(list)
        
        for record in records:
            exposure_log = record.get('exposure_log', {})
            if isinstance(exposure_log, dict):
                exposure_by_type = exposure_log.get('exposure_by_type', {})
                for edc_type in edc_types:
                    if edc_type in exposure_by_type:
                        edc_exposures[edc_type].append(exposure_by_type[edc_type])
        
        # Calculate statistics for each EDC type
        patterns = {}
        for edc_type, exposures in edc_exposures.items():
            if exposures:
                import statistics
                patterns[edc_type] = {
                    'mean_exposure': statistics.mean(exposures),
                    'median_exposure': statistics.median(exposures),
                    'max_exposure': max(exposures),
                    'users_exposed': len(exposures),
                    'high_exposure_count': sum(1 for e in exposures if e > self.risk_thresholds['edc_exposure_high'])
                }
        
        return {
            'edc_patterns': patterns,
            'total_users': len(records),
            'demographics': self.anonymization_service._parse_group_key(
                list(records[0].keys())[0] if records else ''
            )
        }
    
    def _calculate_condition_prevalence(
        self,
        records: List[Dict[str, Any]],
        conditions: List[str]
    ) -> Dict[str, float]:
        """Calculate prevalence rates for specified conditions"""
        total_users = len(records)
        condition_counts = defaultdict(int)
        
        for record in records:
            user_conditions = record.get('conditions', [])
            for condition in user_conditions:
                if isinstance(condition, dict):
                    condition_name = condition.get('name', '').lower()
                    for target_condition in conditions:
                        if target_condition.lower() in condition_name:
                            condition_counts[target_condition] += 1
                            break
        
        # Calculate prevalence rates
        prevalence = {}
        for condition in conditions:
            count = condition_counts.get(condition, 0)
            prevalence[condition] = count / total_users if total_users > 0 else 0
        
        return prevalence
    
    def _determine_severity(self, effect_size: float) -> str:
        """Determine severity level based on effect size"""
        abs_effect = abs(effect_size)
        if abs_effect >= 0.8:
            return 'critical'
        elif abs_effect >= 0.5:
            return 'high'
        elif abs_effect >= 0.2:
            return 'medium'
        else:
            return 'low'
    
    def _generate_executive_summary(
        self,
        aggregate_metrics: Dict[str, Any],
        prevalence_data: Dict[str, Any],
        risk_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary for the report"""
        population_metrics = aggregate_metrics.get('population_metrics', {})
        overall_prevalence = prevalence_data.get('overall_prevalence', {})
        detected_patterns = risk_patterns.get('risk_patterns', [])
        
        # Identify key findings
        key_findings = []
        
        # PCOS prevalence
        pcos_rate = overall_prevalence.get('pcos', 0)
        if pcos_rate > 0:
            key_findings.append(f"PCOS prevalence: {pcos_rate:.1%}")
        
        # PPD prevalence
        ppd_rate = overall_prevalence.get('ppd', 0) + overall_prevalence.get('postpartum depression', 0)
        if ppd_rate > 0:
            key_findings.append(f"PPD prevalence: {ppd_rate:.1%}")
        
        # Anemia prevalence
        anemia_rate = overall_prevalence.get('anemia', 0)
        if anemia_rate > 0:
            key_findings.append(f"Anemia prevalence: {anemia_rate:.1%}")
        
        # Critical risk patterns
        critical_patterns = [p for p in detected_patterns if p.get('severity') == 'critical']
        high_patterns = [p for p in detected_patterns if p.get('severity') == 'high']
        
        return {
            'total_users': population_metrics.get('total_users', 0),
            'key_findings': key_findings,
            'critical_risk_patterns': len(critical_patterns),
            'high_risk_patterns': len(high_patterns),
            'total_risk_patterns': len(detected_patterns),
            'average_toxicity_score': population_metrics.get('average_toxicity_score', 0),
            'average_hormonal_score': population_metrics.get('average_hormonal_score', 0)
        }
    
    def _generate_summary_report(
        self,
        aggregate_metrics: Dict[str, Any],
        prevalence_data: Dict[str, Any],
        risk_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary report"""
        return {
            'report_type': 'summary',
            'executive_summary': self._generate_executive_summary(
                aggregate_metrics,
                prevalence_data,
                risk_patterns
            ),
            'condition_prevalence': prevalence_data.get('overall_prevalence', {}),
            'risk_patterns_summary': {
                'total_patterns': risk_patterns.get('total_patterns_detected', 0),
                'by_severity': self._group_patterns_by_severity(
                    risk_patterns.get('risk_patterns', [])
                )
            }
        }
    
    def _generate_trends_report(
        self,
        user_records: List[Dict[str, Any]],
        time_range: Optional[Dict[str, datetime]]
    ) -> Dict[str, Any]:
        """Generate trends report over time"""
        # This would require historical data analysis
        # For now, return a placeholder structure
        return {
            'report_type': 'trends',
            'time_range': time_range,
            'trends': {
                'pcos_prevalence_trend': 'stable',
                'ppd_prevalence_trend': 'stable',
                'anemia_prevalence_trend': 'stable',
                'edc_exposure_trend': 'stable'
            },
            'note': 'Trend analysis requires historical data collection over multiple time periods'
        }
    
    def _generate_recommendations(
        self,
        risk_patterns: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on detected risk patterns"""
        recommendations = []
        detected_patterns = risk_patterns.get('risk_patterns', [])
        
        for pattern in detected_patterns:
            pattern_type = pattern.get('type')
            severity = pattern.get('severity')
            
            if pattern_type == 'edc_pcos_correlation':
                recommendations.append({
                    'priority': severity,
                    'category': 'environmental_health',
                    'recommendation': f"Implement targeted EDC reduction programs for {pattern.get('edc_type')} exposure",
                    'rationale': pattern.get('description')
                })
            
            elif pattern_type == 'high_pcos_prevalence':
                recommendations.append({
                    'priority': severity,
                    'category': 'reproductive_health',
                    'recommendation': 'Scale up PCOS screening and management programs',
                    'rationale': pattern.get('description')
                })
            
            elif pattern_type == 'high_ppd_prevalence':
                recommendations.append({
                    'priority': severity,
                    'category': 'mental_health',
                    'recommendation': 'Expand postpartum mental health support services',
                    'rationale': pattern.get('description')
                })
            
            elif pattern_type == 'regional_high_edc':
                recommendations.append({
                    'priority': severity,
                    'category': 'regional_intervention',
                    'recommendation': f"Investigate EDC sources in {pattern.get('region')} region and implement mitigation measures",
                    'rationale': pattern.get('description')
                })
            
            elif pattern_type == 'occupational_heat_risk':
                recommendations.append({
                    'priority': severity,
                    'category': 'occupational_health',
                    'recommendation': f"Implement heat safety protocols for {pattern.get('occupation')} workers",
                    'rationale': pattern.get('description')
                })
        
        return recommendations
    
    def _group_patterns_by_severity(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Group risk patterns by severity level"""
        severity_counts = defaultdict(int)
        for pattern in patterns:
            severity = pattern.get('severity', 'unknown')
            severity_counts[severity] += 1
        return dict(severity_counts)
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID"""
        import hashlib
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
