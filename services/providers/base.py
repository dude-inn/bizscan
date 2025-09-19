# -*- coding: utf-8 -*-
"""
Unified provider interface for company data sources
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple


class CompanyProvider(ABC):
    """
    Abstract base class for company data providers
    """
    
    @abstractmethod
    def resolve_by_query(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve company by name query to INN/OGRN
        
        Args:
            query: Company name or search query
            
        Returns:
            Tuple of (inn, ogrn) or (None, None) if not found
        """
        pass
    
    @abstractmethod
    def get_counterparty(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """
        Get company counterparty information
        
        Args:
            inn: Company INN
            ogrn: Company OGRN
            
        Returns:
            Raw API response data
        """
        pass
    
    @abstractmethod
    def get_finance(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """
        Get company financial data
        
        Args:
            inn: Company INN
            ogrn: Company OGRN
            
        Returns:
            Raw API response data
        """
        pass
    
    @abstractmethod
    def get_paid_taxes(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None) -> Dict[str, Any]:
        """
        Get company paid taxes data
        
        Args:
            inn: Company INN
            ogrn: Company OGRN
            
        Returns:
            Raw API response data
        """
        pass
    
    @abstractmethod
    def get_arbitration_cases(self, *, inn: Optional[str] = None, ogrn: Optional[str] = None, 
                            limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """
        Get company arbitration cases
        
        Args:
            inn: Company INN
            ogrn: Company OGRN
            limit: Maximum number of cases to return
            offset: Number of cases to skip
            
        Returns:
            Raw API response data
        """
        pass
