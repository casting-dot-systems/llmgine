"""Typed Notion API client wrapper."""

import logging
from typing import Any, Dict, List, Optional, Union

from notion_client import AsyncClient, Client
from notion_client.errors import APIResponseError, RequestTimeoutError
from pydantic import BaseModel, Field

from .exceptions import (
    NotionAPIError,
    NotionAuthError,
    NotionFrameworkError,
    NotionRateLimitError,
)

logger = logging.getLogger(__name__)


class NotionClientConfig(BaseModel):
    """Configuration for the Notion client."""
    
    auth: str = Field(..., description="Notion API token")
    notion_version: str = Field(default="2022-06-28", description="Notion API version")
    timeout_ms: int = Field(default=60000, description="Request timeout in milliseconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")


class NotionClient:
    """Typed wrapper around the Notion API client."""
    
    def __init__(self, config: Union[NotionClientConfig, str]) -> None:
        if isinstance(config, str):
            # If a string is passed, treat it as the auth token
            self.config = NotionClientConfig(auth=config)
        else:
            self.config = config
        self._sync_client: Optional[Client] = None
        self._async_client: Optional[AsyncClient] = None
        
    @property
    def sync_client(self) -> Client:
        """Get the synchronous Notion client."""
        if self._sync_client is None:
            self._sync_client = Client(
                auth=self.config.auth,
                notion_version=self.config.notion_version,
                timeout_ms=self.config.timeout_ms,
            )
        return self._sync_client
        
    @property
    def async_client(self) -> AsyncClient:
        """Get the asynchronous Notion client."""
        if self._async_client is None:
            self._async_client = AsyncClient(
                auth=self.config.auth,
                notion_version=self.config.notion_version,
                timeout_ms=self.config.timeout_ms,
            )
        return self._async_client
    
    def _handle_api_error(self, error: Exception) -> NotionFrameworkError:
        """Convert Notion API errors to framework errors."""
        if isinstance(error, APIResponseError):
            if error.status == 401:
                return NotionAuthError("Invalid or expired API token")
            elif error.status == 429:
                return NotionRateLimitError("Rate limit exceeded")
            else:
                return NotionAPIError(
                    message=str(error),
                    status_code=error.status,
                    error_code=getattr(error, 'code', None),
                )
        elif isinstance(error, RequestTimeoutError):
            return NotionAPIError("Request timeout", status_code=408)
        else:
            return NotionFrameworkError(f"Unexpected error: {error}")
    
    async def get_database(self, database_id: str) -> Dict[str, Any]:
        """Retrieve a database by ID."""
        try:
            response = await self.async_client.databases.retrieve(database_id=database_id)
            logger.info(f"Retrieved database {database_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve database {database_id}: {e}")
            raise self._handle_api_error(e)
    
    async def query_database(
        self,
        database_id: str,
        filter_obj: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        start_cursor: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Query a database with optional filters and sorts."""
        try:
            query_params = {"database_id": database_id}
            
            if filter_obj:
                query_params["filter"] = filter_obj
            if sorts:
                query_params["sorts"] = sorts
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            if page_size:
                query_params["page_size"] = page_size
                
            response = await self.async_client.databases.query(**query_params)
            logger.info(f"Queried database {database_id}, got {len(response['results'])} results")
            return response
        except Exception as e:
            logger.error(f"Failed to query database {database_id}: {e}")
            raise self._handle_api_error(e)
    
    async def create_page(
        self,
        parent: Dict[str, Any],
        properties: Dict[str, Any],
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a new page."""
        try:
            page_data = {
                "parent": parent,
                "properties": properties,
            }
            
            if children:
                page_data["children"] = children
                
            response = await self.async_client.pages.create(**page_data)
            logger.info(f"Created page {response['id']}")
            return response
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            raise self._handle_api_error(e)
    
    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any],
        archived: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update an existing page."""
        try:
            update_data = {
                "page_id": page_id,
                "properties": properties,
            }
            
            if archived is not None:
                update_data["archived"] = archived
                
            response = await self.async_client.pages.update(**update_data)
            logger.info(f"Updated page {page_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to update page {page_id}: {e}")
            raise self._handle_api_error(e)
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a page by ID."""
        try:
            response = await self.async_client.pages.retrieve(page_id=page_id)
            logger.info(f"Retrieved page {page_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve page {page_id}: {e}")
            raise self._handle_api_error(e)
    
    async def get_users(self) -> List[Dict[str, Any]]:
        """Get all users in the workspace."""
        try:
            response = await self.async_client.users.list()
            logger.info(f"Retrieved {len(response['results'])} users")
            return response["results"]
        except Exception as e:
            logger.error(f"Failed to retrieve users: {e}")
            raise self._handle_api_error(e)
    
    async def search(
        self,
        query: Optional[str] = None,
        filter_obj: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None,
        start_cursor: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Search for pages and databases."""
        try:
            search_params = {}
            
            if query:
                search_params["query"] = query
            if filter_obj:
                search_params["filter"] = filter_obj
            if sort:
                search_params["sort"] = sort
            if start_cursor:
                search_params["start_cursor"] = start_cursor
            if page_size:
                search_params["page_size"] = page_size
                
            response = await self.async_client.search(**search_params)
            logger.info(f"Search returned {len(response['results'])} results")
            return response
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise self._handle_api_error(e)
    
    @classmethod
    def from_token(cls, token: str, **kwargs: Any) -> "NotionClient":
        """Create a client from an API token."""
        config = NotionClientConfig(auth=token, **kwargs)
        return cls(config)
    
    async def close(self) -> None:
        """Close the async client connections."""
        if self._async_client:
            # The notion_client AsyncClient doesn't have a close method
            # Just clean up our reference
            self._async_client = None
            
    async def __aenter__(self) -> "NotionClient":
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
