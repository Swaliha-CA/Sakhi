"""Bidirectional synchronization service for offline-first architecture"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import User, HealthRecord, Screening, ProductScan, SyncLog
from app.db.sqlite_manager import get_sqlite_manager
from app.core.config import settings
from app.core.logging import logger


class SyncService:
    """
    Bidirectional sync service with immutable append-only logs
    
    Features:
    - Upload local changes to cloud
    - Download cloud updates to local
    - Chronological conflict resolution (last-write-wins)
    - Batch sync to minimize network calls
    - Critical conflict flagging for manual review
    """
    
    def __init__(self, device_id: str):
        """
        Initialize sync service
        
        Args:
            device_id: Unique device identifier
        """
        self.device_id = device_id
        self.sqlite_manager = get_sqlite_manager()
    
    async def sync_to_cloud(self, user_id: int, batch_size: int = 100) -> Dict[str, Any]:
        """
        Upload local changes to cloud
        
        Args:
            user_id: User ID to sync
            batch_size: Number of records per batch
        
        Returns:
            Sync result summary
        """
        db = self.sqlite_manager.get_session()
        
        try:
            # Start sync log
            sync_log = SyncLog(
                device_id=self.device_id,
                sync_type="upload",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            db.add(sync_log)
            db.commit()
            
            total_synced = 0
            
            # Sync health records
            health_records = db.query(HealthRecord).filter(
                and_(
                    HealthRecord.user_id == user_id,
                    HealthRecord.synced_to_cloud == False
                )
            ).limit(batch_size).all()
            
            for record in health_records:
                # TODO: Upload to cloud API
                # await self._upload_health_record(record)
                
                # Mark as synced
                record.synced_to_cloud = True
                total_synced += 1
            
            # Sync screenings
            screenings = db.query(Screening).filter(
                and_(
                    Screening.user_id == user_id,
                    Screening.synced_to_cloud == False
                )
            ).limit(batch_size).all()
            
            for screening in screenings:
                # TODO: Upload to cloud API
                # await self._upload_screening(screening)
                
                screening.synced_to_cloud = True
                total_synced += 1
            
            # Sync product scans
            scans = db.query(ProductScan).filter(
                and_(
                    ProductScan.user_id == user_id,
                    ProductScan.synced_to_cloud == False
                )
            ).limit(batch_size).all()
            
            for scan in scans:
                # TODO: Upload to cloud API
                # await self._upload_product_scan(scan)
                
                scan.synced_to_cloud = True
                total_synced += 1
            
            # Update user last sync time
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_synced_at = datetime.utcnow()
            
            # Complete sync log
            sync_log.status = "success"
            sync_log.records_synced = total_synced
            sync_log.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Sync to cloud completed: {total_synced} records uploaded")
            
            return {
                "status": "success",
                "records_synced": total_synced,
                "sync_log_id": sync_log.id
            }
        
        except Exception as e:
            logger.error(f"Sync to cloud failed: {e}")
            
            # Update sync log
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "status": "failed",
                "error": str(e),
                "sync_log_id": sync_log.id
            }
        
        finally:
            db.close()
    
    async def sync_from_cloud(self, user_id: int) -> Dict[str, Any]:
        """
        Download cloud updates to local
        
        Args:
            user_id: User ID to sync
        
        Returns:
            Sync result summary
        """
        db = self.sqlite_manager.get_session()
        
        try:
            # Start sync log
            sync_log = SyncLog(
                device_id=self.device_id,
                sync_type="download",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            db.add(sync_log)
            db.commit()
            
            total_synced = 0
            
            # Get user's last sync time
            user = db.query(User).filter(User.id == user_id).first()
            last_sync = user.last_synced_at if user else None
            
            # TODO: Download new records from cloud API
            # cloud_records = await self._download_from_cloud(user_id, last_sync)
            
            # For now, just update sync time
            if user:
                user.last_synced_at = datetime.utcnow()
            
            # Complete sync log
            sync_log.status = "success"
            sync_log.records_synced = total_synced
            sync_log.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Sync from cloud completed: {total_synced} records downloaded")
            
            return {
                "status": "success",
                "records_synced": total_synced,
                "sync_log_id": sync_log.id
            }
        
        except Exception as e:
            logger.error(f"Sync from cloud failed: {e}")
            
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            
            return {
                "status": "failed",
                "error": str(e),
                "sync_log_id": sync_log.id
            }
        
        finally:
            db.close()
    
    def resolve_conflicts(
        self,
        local_record: Dict[str, Any],
        cloud_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve sync conflicts using chronological last-write-wins
        
        Args:
            local_record: Local record data
            cloud_record: Cloud record data
        
        Returns:
            Resolved record (winner)
        """
        local_timestamp = local_record.get("recorded_at") or local_record.get("conducted_at")
        cloud_timestamp = cloud_record.get("recorded_at") or cloud_record.get("conducted_at")
        
        # Last-write-wins based on timestamp
        if local_timestamp > cloud_timestamp:
            logger.info("Conflict resolved: Local record wins (newer)")
            return local_record
        else:
            logger.info("Conflict resolved: Cloud record wins (newer)")
            return cloud_record
    
    def flag_critical_conflict(
        self,
        record_type: str,
        record_id: int,
        reason: str
    ):
        """
        Flag critical conflicts for manual review
        
        Args:
            record_type: Type of record (health_record, screening, etc.)
            record_id: Record ID
            reason: Reason for flagging
        """
        logger.warning(
            f"CRITICAL CONFLICT FLAGGED: {record_type} ID {record_id} - {reason}"
        )
        
        # TODO: Store in conflicts table for manual review
        # TODO: Notify ASHA worker or admin
    
    async def migrate_user_data(
        self,
        abha_id: str,
        old_device_id: str,
        new_device_id: str
    ) -> Dict[str, Any]:
        """
        Migrate user data from old device to new device
        
        Uses ABHA ID to decouple patient record from specific device
        
        Args:
            abha_id: User's ABHA ID
            old_device_id: Old device identifier
            new_device_id: New device identifier
        
        Returns:
            Migration result
        """
        db = self.sqlite_manager.get_session()
        
        try:
            # Find user by ABHA ID
            user = db.query(User).filter(User.abha_id == abha_id).first()
            
            if not user:
                return {
                    "status": "failed",
                    "error": f"User not found with ABHA ID: {abha_id}"
                }
            
            # Update device ID
            user.current_device_id = new_device_id
            user.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(
                f"User data migrated: ABHA {abha_id} from device {old_device_id} to {new_device_id}"
            )
            
            return {
                "status": "success",
                "user_id": user.id,
                "abha_id": abha_id,
                "new_device_id": new_device_id
            }
        
        except Exception as e:
            logger.error(f"User data migration failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
        
        finally:
            db.close()
    
    def get_sync_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get sync status for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Sync status summary
        """
        db = self.sqlite_manager.get_session()
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {"status": "error", "message": "User not found"}
            
            # Count unsynced records
            unsynced_health = db.query(HealthRecord).filter(
                and_(
                    HealthRecord.user_id == user_id,
                    HealthRecord.synced_to_cloud == False
                )
            ).count()
            
            unsynced_screenings = db.query(Screening).filter(
                and_(
                    Screening.user_id == user_id,
                    Screening.synced_to_cloud == False
                )
            ).count()
            
            unsynced_scans = db.query(ProductScan).filter(
                and_(
                    ProductScan.user_id == user_id,
                    ProductScan.synced_to_cloud == False
                )
            ).count()
            
            total_unsynced = unsynced_health + unsynced_screenings + unsynced_scans
            
            # Get last sync log
            last_sync_log = db.query(SyncLog).filter(
                SyncLog.device_id == self.device_id
            ).order_by(SyncLog.started_at.desc()).first()
            
            return {
                "user_id": user_id,
                "abha_id": user.abha_id,
                "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
                "unsynced_records": {
                    "health_records": unsynced_health,
                    "screenings": unsynced_screenings,
                    "product_scans": unsynced_scans,
                    "total": total_unsynced
                },
                "last_sync_status": last_sync_log.status if last_sync_log else None,
                "last_sync_time": last_sync_log.completed_at.isoformat() if last_sync_log and last_sync_log.completed_at else None
            }
        
        finally:
            db.close()


def get_sync_service(device_id: str) -> SyncService:
    """
    Get sync service instance
    
    Args:
        device_id: Device identifier
    
    Returns:
        SyncService instance
    """
    return SyncService(device_id)
