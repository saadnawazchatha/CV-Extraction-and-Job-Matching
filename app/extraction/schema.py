from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


OptionalText = Annotated[str | None, AfterValidator(lambda text: text or None)]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Experience(_Record):
    title: OptionalText
    company: OptionalText
    period: OptionalText
    highlights: list[str] = Field(max_length=4)


class Education(_Record):
    degree: OptionalText
    school: OptionalText
    year: Annotated[int, Field(ge=1000, le=9999)] | None


class CV(_Record):
    """Gemma must supply every key, including missing values as null or empty lists."""

    name: OptionalText
    email: OptionalText
    phone: OptionalText
    location: OptionalText
    linkedin: OptionalText
    github: OptionalText
    summary: OptionalText
    skills: list[str]
    experience: list[Experience]
    education: list[Education]
