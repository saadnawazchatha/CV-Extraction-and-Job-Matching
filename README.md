
# CV Project — CV Data Extraction & AI-Based Job Matching

## Project Overview

A Python-based microservice developed to overcome the limitations of traditional Regex-based CV extraction.

The project aims to extract structured candidate information from CVs and eventually use AI-based techniques to match candidates against job descriptions.

## Project Workflow

1. **Document Upload:** Accept CVs in PDF, Word, and image formats.
2. **Raw Text Extraction:** Extract text using dedicated document parsers and OCR where required.
3. **Information Extraction (Next Focus):** Convert raw text into useful candidate information in JSON format.
4. **AI-Based Job Matching (Future):** Match extracted candidate information against job descriptions.

---

## Development Progress

### Phase 1 — Raw Text Extraction

**Status: ✅ Completed**

| Feature | Status |
|---------|--------|
| Text extraction from Word documents | ✅ Completed |
| Text extraction from PDFs | ✅ Completed |
| OCR-based extraction from images | ✅ Completed |
| Scanned PDF processing using OCR | ✅ Completed |
| OCR for images embedded in Word documents | ✅ Completed |
| Return uploaded filename and extracted raw text | ✅ Completed |

### Latest Improvements — November 20, 2026

The existing extraction pipeline has been refined to provide:

- **Improved accuracy** across PDF, Word, and image-based CVs.
- **Better text structure** and organization of extracted content.
- **Cleaner, more readable output** for downstream AI processing.
- **Completed OCR support** for images embedded in Word documents.

These improvements prepare the extracted raw text for structured information extraction.

---

### Phase 2 — Structured Information Extraction

**Status: 🔄 Next Focus**

The next step is to develop an AI-based extraction system that converts raw CV text into useful, structured candidate information.

The target information includes:

- **Personal Details:** Name, email, phone, and location.
- **Professional Profiles:** LinkedIn and GitHub.
- **Professional Information:** Summary and skills.
- **Work Experience:** Job title, company, employment period, and highlights.
- **Education:** Degree, institution, and graduation year.

#### Desired JSON Output

The following is an example of the expected response once structured information extraction is implemented.

**Note:** This is the planned output format, not the current microservice response.

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+15551234567",
  "location": "New York, NY",
  "linkedin": "https://www.linkedin.com/in/johndoe",
  "github": null,
  "summary": "Software Developer experienced in designing, developing, and maintaining software applications.",
  "skills": [
    "Python",
    "Java",
    "Software Development",
    "Unit Testing",
    "Code Optimization",
    "Debugging",
    "SQL",
    "HTML",
    "CSS",
    "JavaScript",
    "Git",
    "REST APIs"
  ],
  "experience": [
    {
      "title": "Software Developer",
      "company": "Example Technologies",
      "period": "Jan 2022 - Present",
      "highlights": [
        "Developed and maintained software applications.",
        "Improved application performance through code optimization.",
        "Collaborated with team members to implement and test new features."
      ]
    }
  ],
  "education": [
    {
      "degree": "Bachelor of Science in Computer Science",
      "school": "Example University",
      "year": 2021
    }
  ]
}
```

Missing information will be represented using `null` or empty arrays rather than fabricated values.

---

### Phase 3 — AI-Based Job Matching

**Status: ⏳ Future Development**

Use extracted candidate information to match CVs against job descriptions and identify the most relevant candidates.

The matching, scoring, and ranking methodology will be determined during this phase.

---

## Current Project Status

**Last Updated:** November 20, 2026

✅ **Completed:** Raw text extraction across all targeted document formats, including OCR support and extraction quality improvements.

🔄 **Next Focus:** Converting extracted raw text into useful, structured candidate information using AI-based methods.

⏳ **Future:** AI-based CV matching against job descriptions.

---

## Installation & Usage

For installation, dependencies, and instructions on running the project, see [how_to_use.md](how_to_use.md).
