"""Singleton homepage marketing content (about section), separate from general CMS document."""
from typing import Optional
from pydantic import BaseModel


class HomepageAboutUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    image: Optional[str] = None
