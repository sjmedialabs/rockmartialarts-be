from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class SEOSettings(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    og_image: Optional[str] = None


class TestimonialItem(BaseModel):
    name: str = ""
    role: str = ""
    quote: Optional[str] = None
    image: Optional[str] = None

    class Config:
        extra = "allow"


class HomepageSection(BaseModel):
    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    hero_description: Optional[str] = None
    hero_image: Optional[str] = None
    hero_video: Optional[str] = None
    about_title: Optional[str] = None
    about_subtitle: Optional[str] = None
    courses_title: Optional[str] = None
    courses_subtitle: Optional[str] = None
    testimonials_title: Optional[str] = None
    testimonials_subtitle: Optional[str] = None
    testimonials: Optional[List[TestimonialItem]] = None
    cta_title: Optional[str] = None
    cta_subtitle: Optional[str] = None
    # Registration flow media (left side image/video/gif)
    registration_media_url: Optional[str] = None
    registration_media_type: Optional[str] = None


class FooterContent(BaseModel):
    footer_text: Optional[str] = None
    copyright_text: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    social_facebook: Optional[str] = None
    social_instagram: Optional[str] = None
    social_twitter: Optional[str] = None
    social_youtube: Optional[str] = None


class BrandingSettings(BaseModel):
    navbar_logo: Optional[str] = None
    footer_logo: Optional[str] = None
    favicon: Optional[str] = None


class CMSContent(BaseModel):
    homepage: Optional[HomepageSection] = HomepageSection()
    footer: Optional[FooterContent] = FooterContent()
    branding: Optional[BrandingSettings] = BrandingSettings()
    page_seo: Optional[Dict[str, SEOSettings]] = {}


class CMSContentUpdate(BaseModel):
    homepage: Optional[HomepageSection] = None
    footer: Optional[FooterContent] = None
    branding: Optional[BrandingSettings] = None
    page_seo: Optional[Dict[str, SEOSettings]] = None


class CMSContentResponse(BaseModel):
    id: str
    homepage: HomepageSection = HomepageSection()
    footer: FooterContent = FooterContent()
    branding: BrandingSettings = BrandingSettings()
    page_seo: Dict[str, SEOSettings] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
