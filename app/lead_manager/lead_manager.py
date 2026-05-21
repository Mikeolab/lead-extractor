"""Core lead manager database operations."""

from typing import List, Dict, Optional, Tuple
import sqlite3
from datetime import datetime
from uuid import uuid4
from app.database.db import get_connection
from app.lead_manager.validator import validate_email
from app.lead_manager.domain_filter import extract_domain


def save_external_leads(
    leads: List[Dict],
    source: str = "manual_upload",
    file_name: Optional[str] = None
) -> Tuple[int, List[str]]:
    """
    Save external leads to database.
    
    Args:
        leads: List of lead dictionaries
        source: Source identifier (default: manual_upload)
        file_name: Original filename if uploaded
        
    Returns:
        Tuple of (count saved, list of error messages)
    """
    if not leads:
        return 0, ["No leads to save"]
    
    errors = []
    batch_id = str(uuid4())
    count = 0
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for lead in leads:
            email = lead.get("email", "").strip()
            if not email:
                continue
            
            # Validate email
            validation = validate_email(email)
            if not validation.is_valid:
                errors.append(f"Invalid email: {email}")
                continue
            
            domain = extract_domain(email)
            
            try:
                cursor.execute(
                    """
                    INSERT INTO external_leads
                    (business_name, contact_name, email, phone, website, domain, 
                     source, file_name, upload_batch_id, is_validated, validation_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead.get("business_name", ""),
                        lead.get("contact_name", ""),
                        email,
                        lead.get("phone", ""),
                        lead.get("website", ""),
                        domain or "",
                        source,
                        file_name or "",
                        batch_id,
                        1,  # is_validated
                        "valid"
                    )
                )
                count += 1
            except sqlite3.IntegrityError:
                # Email already exists, skip
                errors.append(f"Email already exists: {email}")
            except Exception as e:
                errors.append(f"Failed to save {email}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if count > 0:
            errors.insert(0, f"Successfully saved {count} leads")
        
        return count, errors
    
    except Exception as e:
        return 0, [f"Database error: {str(e)}"]


def get_external_leads(
    limit: int = 10000,
    offset: int = 0,
    domain_filter: Optional[str] = None
) -> List[Dict]:
    """
    Get external leads from database.
    
    Args:
        limit: Maximum leads to return
        offset: Offset for pagination
        domain_filter: Optional domain filter
        
    Returns:
        List of lead dictionaries
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, business_name, contact_name, email, phone, website, domain, source, created_at FROM external_leads"
        params = []
        
        if domain_filter:
            query += " WHERE domain LIKE ?"
            params.append(f"%{domain_filter}%")
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        leads = []
        for row in rows:
            leads.append({
                "id": row[0],
                "business_name": row[1],
                "contact_name": row[2],
                "email": row[3],
                "phone": row[4],
                "website": row[5],
                "domain": row[6],
                "source": row[7],
                "created_at": row[8]
            })
        
        conn.close()
        return leads
    
    except Exception as e:
        print(f"Error fetching external leads: {str(e)}")
        return []


def get_external_leads_by_domain(domain: str) -> List[Dict]:
    """
    Get external leads for a specific domain.
    
    Args:
        domain: Domain to filter by
        
    Returns:
        List of leads for the domain
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, business_name, contact_name, email, phone, website, domain, source, created_at 
            FROM external_leads 
            WHERE domain = ? 
            ORDER BY created_at DESC
            """,
            (domain,)
        )
        rows = cursor.fetchall()
        
        leads = []
        for row in rows:
            leads.append({
                "id": row[0],
                "business_name": row[1],
                "contact_name": row[2],
                "email": row[3],
                "phone": row[4],
                "website": row[5],
                "domain": row[6],
                "source": row[7],
                "created_at": row[8]
            })
        
        conn.close()
        return leads
    
    except Exception as e:
        print(f"Error fetching external leads by domain: {str(e)}")
        return []


def get_domain_statistics() -> Dict[str, int]:
    """
    Get statistics about domains in external leads.
    
    Returns:
        Dictionary with domain as key and count as value
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT domain, COUNT(*) as count 
            FROM external_leads 
            WHERE domain IS NOT NULL AND domain != ''
            GROUP BY domain 
            ORDER BY count DESC
            """
        )
        rows = cursor.fetchall()
        
        stats = {}
        for row in rows:
            stats[row[0]] = row[1]
        
        conn.close()
        return stats
    
    except Exception as e:
        print(f"Error fetching domain statistics: {str(e)}")
        return {}


def compare_with_extracted_leads(external_email: str) -> Optional[Dict]:
    """
    Compare external lead with extracted leads (check for duplicates).
    
    Args:
        external_email: Email to check
        
    Returns:
        Dictionary with match info if found, None otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check for exact email match in extracted leads
        cursor.execute(
            """
            SELECT l.id, l.business_name, l.contact_name, l.email, s.query, s.created_at
            FROM leads l
            JOIN searches s ON l.search_id = s.id
            WHERE LOWER(l.email) = LOWER(?)
            LIMIT 1
            """,
            (external_email,)
        )
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "found": True,
                "lead_id": row[0],
                "business_name": row[1],
                "contact_name": row[2],
                "email": row[3],
                "query": row[4],
                "created_at": row[5],
                "match_type": "exact"
            }
        
        return None
    
    except Exception as e:
        print(f"Error comparing with extracted leads: {str(e)}")
        return None


def get_external_leads_count() -> int:
    """Get total count of external leads."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM external_leads")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    except Exception:
        return 0


def delete_external_leads(lead_ids: List[int]) -> Tuple[int, str]:
    """
    Delete external leads by ID.
    
    Args:
        lead_ids: List of lead IDs to delete
        
    Returns:
        Tuple of (count deleted, status message)
    """
    if not lead_ids:
        return 0, "No leads to delete"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(lead_ids))
        cursor.execute(
            f"DELETE FROM external_leads WHERE id IN ({placeholders})",
            lead_ids
        )
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count, f"Deleted {deleted_count} leads"
    
    except Exception as e:
        return 0, f"Error deleting leads: {str(e)}"


def delete_external_leads_by_batch(batch_id: str) -> Tuple[int, str]:
    """
    Delete all external leads from a batch.
    
    Args:
        batch_id: Batch ID to delete
        
    Returns:
        Tuple of (count deleted, status message)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM external_leads WHERE upload_batch_id = ?", (batch_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count, f"Deleted batch {batch_id}: {deleted_count} leads"
    
    except Exception as e:
        return 0, f"Error deleting batch: {str(e)}"
