"""Content contract v1 - the source of truth for everything a generated site renders.

Chain (one direction only, ADR-004):

    this module (Pydantic)  ->  packages/contracts/content.schema.json  ->  TS types + Ajv

Rules encoded here, taken from the architecture documents:

- **AI generates DATA, not CODE** (`docs/ARCHITECTURE.md` §1). Every string a site renders lives in
  a validated content artifact; no React component contains client copy.
- `content_schema_version` is enforced, not decorative (ADR-005), and a template declares which
  versions it supports (ADR-006). See `sites/_template-base/template.config.ts`.
- **All prose is plain text** (`list[str]` paragraphs). There is deliberately no HTML or markdown
  field, so no generated site ever needs `dangerouslySetInnerHTML` or a sanitizer
  (`docs/SECURITY-AND-RISKS.md`).
- Copy may only derive from approved `client_facts` (`docs/DOMAIN-MODEL.md`). That rule is enforced
  upstream in the pipeline; this schema only guarantees shape and completeness.
- German legal pages are part of the model (`docs/PIPELINE-AND-GATE.md`, check
  `required_legal_pages`). A site cannot be represented without Impressum and Datenschutz content.

Changing anything here is a content-model change: bump `CONTENT_SCHEMA_VERSION` and update the
templates' `SUPPORTED_CONTENT_SCHEMA_VERSIONS`.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

CONTENT_SCHEMA_VERSION = "1.0.0"

# --- primitive constraints ---------------------------------------------------------------------

Paragraph = Annotated[str, Field(min_length=1, max_length=2000)]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
Line = Annotated[str, Field(min_length=1, max_length=300)]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
TimeOfDay = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
GermanPostalCode = Annotated[str, Field(pattern=r"^\d{5}$")]
HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
SameOriginPath = Annotated[str, Field(pattern=r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$")]
InternalHref = Annotated[str, Field(pattern=r"^(/(?:[A-Za-z0-9._~!$&'()*+,;=:@%/-]*)?|#[a-z0-9-]+)$")]
EmailAddress = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")]

Weekday = Literal["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
IconName = Literal[
    "tooth",
    "sparkle",
    "shield",
    "clock",
    "phone",
    "map-pin",
    "users",
    "heart",
    "child",
    "calendar",
]
SpokenLanguage = Literal["de", "en"]
InsuranceKind = Literal["gesetzlich", "privat", "selbstzahler"]
PagePath = Literal["/", "/leistungen", "/impressum", "/datenschutz"]


class ContentBase(BaseModel):
    """Base for every content node: unknown fields are a validation error, never ignored."""

    model_config = ConfigDict(extra="forbid")


# --- artifact metadata and site identity --------------------------------------------------------


class ContentMeta(ContentBase):
    """Artifact-level metadata. Not rendered, except the fixture banner (see `is_fixture`)."""

    client_slug: Slug = Field(description="Client entity slug (docs/DOMAIN-MODEL.md `clients.slug`).")
    is_fixture: bool = Field(
        description="True for demo/fixture content. The build gate refuses to publish fixture content."
    )
    note: Paragraph | None = Field(
        default=None, description="Human note. Never rendered as HTML, never part of the page copy."
    )


class SiteIdentity(ContentBase):
    name: ShortText
    short_name: Line | None = None
    tagline: ShortText
    url: HttpUrl = Field(description="Canonical origin of the site, e.g. https://praxis.example")
    description: Annotated[str, Field(min_length=50, max_length=170)] = Field(
        description="Default meta description, also used as the llms.txt summary."
    )
    theme_color: HexColor
    og_image: SameOriginPath | None = Field(
        default=None, description="Same-origin path of a build-time generated OG image."
    )

# --- business facts (rendered on the site *and* used for JSON-LD) -------------------------------


class Address(ContentBase):
    street: ShortText
    postal_code: GermanPostalCode
    city: ShortText
    region: Line | None = None
    country: Literal["DE"] = "DE"


class GeoPoint(ContentBase):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class ContactDetails(ContentBase):
    phone: ShortText = Field(description="Human readable phone number.")
    email: EmailAddress
    emergency_phone: ShortText | None = None
    emergency_note: Paragraph | None = None


class OpeningSlot(ContentBase):
    opens: TimeOfDay
    closes: TimeOfDay


class OpeningHours(ContentBase):
    days: Annotated[list[Weekday], Field(min_length=1)]
    slots: Annotated[list[OpeningSlot], Field(min_length=1)]
    note: Paragraph | None = None


class Accessibility(ContentBase):
    step_free_entrance: bool
    elevator: bool
    accessible_toilet: bool
    notes: Paragraph | None = None


class MapInfo(ContentBase):
    link_url: HttpUrl = Field(
        description="Map opened by user click. No third-party embed and no cookie before consent."
    )
    link_label: ShortText
    note: Paragraph | None = None


class Business(ContentBase):
    """Typed business truth. Every value must trace back to an approved `client_fact`."""

    legal_name: ShortText
    brand_name: ShortText
    business_type: Literal["dental_clinic"] = Field(
        description="Allowlisted category -> JSON-LD type mapping (deterministic, ADR-013)."
    )
    jurisdiction: Literal["DE"] = Field(
        description="Drives which legal pages are required (ADR-014)."
    )
    address: Address
    geo: GeoPoint
    contact: ContactDetails
    opening_hours: Annotated[list[OpeningHours], Field(min_length=1)]
    spoken_languages: Annotated[list[SpokenLanguage], Field(min_length=1)]
    insurance: Annotated[list[InsuranceKind], Field(min_length=1)]
    payment_methods: Annotated[list[Line], Field(min_length=1)]
    price_range: Line | None = Field(default=None, description="schema.org priceRange, e.g. '$$'.")
    accessibility: Accessibility
    parking: Paragraph | None = None
    public_transport: Paragraph | None = None
    map: MapInfo


class Compliance(ContentBase):
    medical_disclaimer: Annotated[list[Paragraph], Field(min_length=1)] = Field(
        description="Rendered in the footer and in llms.txt. Required for health categories."
    )
    legal_review_status: Literal["pending", "reviewed"] = Field(
        description="A German lawyer reviews Impressum/Datenschutz/disclaimer once "
        "(docs/SECURITY-AND-RISKS.md). Production mode of the gate blocks `pending`."
    )
    notes: Paragraph | None = None

    og_image_alt: Line | None = None


class Cta(ContentBase):
    label: ShortText
    href: InternalHref

# --- page sections -----------------------------------------------------------------------------


class HeroSection(ContentBase):
    eyebrow: Line | None = None
    headline: ShortText
    subheadline: Annotated[str, Field(min_length=1, max_length=400)]
    paragraphs: Annotated[list[Paragraph], Field(min_length=1)]
    primary_cta: Cta
    secondary_cta: Cta | None = None


class Highlight(ContentBase):
    icon: IconName
    title: ShortText
    body: Paragraph


class Service(ContentBase):
    id: Slug = Field(description="Anchor id and stable reference; never localised.")
    title: ShortText
    summary: Annotated[str, Field(min_length=1, max_length=400)]
    paragraphs: Annotated[list[Paragraph], Field(min_length=1)]
    features: list[Line] = Field(default_factory=list)
    icon: IconName


class ServicesSection(ContentBase):
    heading: ShortText
    intro: Annotated[list[Paragraph], Field(min_length=1)]
    note: Paragraph | None = None
    items: Annotated[list[Service], Field(min_length=1)]


class TeamMember(ContentBase):
    id: Slug
    name: ShortText
    role: ShortText
    qualifications: Annotated[list[Line], Field(min_length=1)]
    focus_areas: list[Line] = Field(default_factory=list)
    languages: Annotated[list[SpokenLanguage], Field(min_length=1)]
    bio: Annotated[list[Paragraph], Field(min_length=1)]
    photo_url: SameOriginPath | None = Field(
        default=None, description="Same-origin path to a client-approved photo; null renders initials."
    )


class TeamSection(ContentBase):
    heading: ShortText
    intro: Annotated[list[Paragraph], Field(min_length=1)]
    members: Annotated[list[TeamMember], Field(min_length=1)]


class HoursSection(ContentBase):
    heading: ShortText
    intro: Annotated[list[Paragraph], Field(min_length=1)]
    appointment_note: Paragraph | None = None
    note: Paragraph | None = None


class ContactFormLabels(ContentBase):
    name: ShortText
    email: ShortText
    phone: ShortText
    phone_optional: ShortText
    message: ShortText
    required_hint: ShortText
    optional_hint: ShortText
    error_required: ShortText
    error_email: ShortText
    error_summary: ShortText


class ContactForm(ContentBase):
    heading: ShortText
    intro: Annotated[list[Paragraph], Field(min_length=1)]
    consent_label: ShortText
    submit_label: ShortText
    submitting_label: ShortText
    success_message: Paragraph
    failure_message: Paragraph
    offline_notice: Paragraph = Field(
        description="Shown when no lead endpoint is configured at build time (v1 scaffold has no backend)."
    )
    labels: ContactFormLabels


class ContactSection(ContentBase):
    heading: ShortText
    intro: Annotated[list[Paragraph], Field(min_length=1)]
    channels_heading: ShortText
    reply_note: Paragraph | None = None
    form: ContactForm


class FaqItem(ContentBase):
    question: ShortText
    answer: Annotated[list[Paragraph], Field(min_length=1)]

# --- legal pages (required for DE) --------------------------------------------------------------


class LegalSection(ContentBase):
    heading: ShortText
    paragraphs: Annotated[list[Paragraph], Field(min_length=1)]


class ProfessionalBody(ContentBase):
    name: ShortText
    url: HttpUrl
    supervising_authority: ShortText


class RegulationRef(ContentBase):
    name: ShortText
    url: HttpUrl


class ResponsiblePerson(ContentBase):
    name: ShortText
    address: Address


class Imprint(ContentBase):
    """Impressum content (DE: section 5 DDG, formerly TMG; section 18 (2) MStV)."""

    provider_name: ShortText
    legal_form: ShortText
    represented_by: Annotated[list[ShortText], Field(min_length=1)]
    address: Address
    contact: ContactDetails
    professional_title: ShortText
    professional_title_country: ShortText
    professional_body: ProfessionalBody
    professional_regulations: Annotated[list[RegulationRef], Field(min_length=1)]
    vat_id: Line | None = None
    responsible_for_content: ResponsiblePerson
    dispute_resolution: Annotated[list[Paragraph], Field(min_length=1)]
    liability_notes: Annotated[list[Paragraph], Field(min_length=1)]
    copyright_notes: Annotated[list[Paragraph], Field(min_length=1)]
    last_updated: date


class Hosting(ContentBase):
    provider: ShortText
    location: ShortText
    note: Paragraph


class Authority(ContentBase):
    name: ShortText
    url: HttpUrl
    address: Address


class Privacy(ContentBase):
    """Datenschutzerklaerung content (DSGVO Art. 13/14)."""

    controller: ResponsiblePerson
    controller_contact: ContactDetails
    data_protection_officer: Paragraph | None = None
    hosting: Hosting
    legal_basis: Annotated[list[LegalSection], Field(min_length=1)]
    data_categories: Annotated[list[LegalSection], Field(min_length=1)]
    recipients: Annotated[list[Paragraph], Field(min_length=1)]
    retention: Annotated[list[Paragraph], Field(min_length=1)]
    rights: Annotated[list[LegalSection], Field(min_length=1)]
    cookies_notice: Paragraph
    contact_form_notice: Paragraph
    no_tracking_notice: Paragraph = Field(
        description="States that no third-party tracker is embedded "
        "(no Google Fonts CDN, no analytics, no map iframe)."
    )
    supervisory_authority: Authority
    last_updated: date


class Legal(ContentBase):
    imprint: Imprint
    privacy: Privacy


# --- SEO manifest inputs -----------------------------------------------------------------------


class PageSeo(ContentBase):
    path: PagePath
    title: Annotated[str, Field(min_length=10, max_length=70)]
    description: Annotated[str, Field(min_length=50, max_length=170)]
    noindex: bool = False


class Seo(ContentBase):
    pages: Annotated[list[PageSeo], Field(min_length=1)] = Field(
        description="One entry per generated page; sitemap, canonical and meta derive from it."
    )


# --- root ----------------------------------------------------------------------------------------


class ContentModel(ContentBase):
    """One immutable content artifact revision (docs/DOMAIN-MODEL.md, artifact type `content_model`)."""

    content_schema_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")] = Field(
        description="Enforced, not decorative (ADR-005). Templates declare the versions they support."
    )
    meta: ContentMeta
    locale: Annotated[str, Field(pattern=r"^[a-z]{2}-[A-Z]{2}$")]
    site: SiteIdentity
    business: Business
    compliance: Compliance
    hero: HeroSection
    highlights: Annotated[list[Highlight], Field(min_length=1)]
    services: ServicesSection
    team: TeamSection
    hours: HoursSection
    contact: ContactSection
    faq: FaqSection
    legal: Legal
    seo: Seo



class FaqSection(ContentBase):
    heading: ShortText
    intro: Paragraph | None = None
    items: Annotated[list[FaqItem], Field(min_length=1)]

