
# CV Project — CV Data Extraction & AI-Based Job Matching

## Project Overview

A Python-based microservice developed to overcome the limitations of traditional Regex-based CV extraction.

The system extracts raw text from CVs, converts it into structured candidate information using AI, and evaluates candidate relevance against job descriptions.

The service supports **three independent processing modes**, allowing users to perform only the operations they require.

## Project Workflow

1. **Document Upload:** Accept CVs in PDF, Word, and image formats.
2. **Raw Text Extraction:** Extract text using dedicated document parsers and OCR.
3. **AI Information Extraction:** Convert raw CV text into structured candidate information.
4. **JSON Response:** Return extracted information in a standardized JSON format.
5. **CV Ranking:** Compare candidate information against job descriptions and generate relevance scores.

---

## Service Modes

The microservice is divided into three independently usable processing modes.

| Mode | Function | Status |
|------|----------|--------|
| **1. Parsing** | Extract raw text from CV documents | ✅ Completed |
| **2. Information Extraction** | Convert raw CV text into structured JSON | ✅ Completed |
| **3. CV Ranking** | Evaluate CV relevance against job descriptions | 🔄 Under Refinement |

Each mode can be used separately depending on the required functionality.

For example, users can request **only raw text extraction**, obtain **structured candidate information without ranking**, or use the **ranking functionality** when candidate evaluation is required.

This modular approach avoids unnecessary processing and provides greater flexibility when integrating the service into other applications.

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
| OCR for embedded images in Word documents | ✅ Completed |
| Improved extraction accuracy and text structure | ✅ Completed |

The parsing pipeline produces accurate, organized, and readable raw text for downstream processing.

---

### Phase 2 — Structured Information Extraction

**Status: ✅ Completed & Tested**

An AI-based information extraction model processes parsed CV text and generates structured candidate information in JSON format.

The extraction model has been tested and validated against the desired JSON structure, completing this development phase.

The extracted information includes:

- **Personal Details:** Name, email, phone, and location.
- **Professional Profiles:** LinkedIn and GitHub.
- **Professional Information:** Summary and skills.
- **Work Experience:** Job title, company, employment period, and highlights.
- **Education:** Degree, institution, and graduation year.

#### JSON Response Format

Example using fictional candidate information:

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+15551234567",
  "location": "New York, NY",
  "linkedin": "https://www.linkedin.com/in/johndoe",
  "github": null,
  "summary": "Software Developer experienced in building and maintaining software applications.",
  "skills": [
    "Python",
    "Java",
    "SQL",
    "JavaScript",
    "REST APIs",
    "Git"
  ],
  "experience": [
    {
      "title": "Software Developer",
      "company": "Example Technologies",
      "period": "Jan 2022 - Present",
      "highlights": [
        "Developed and maintained software applications.",
        "Improved application performance through code optimization."
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

Missing information is represented using `null` or empty arrays rather than fabricated values.

---

### Phase 3 — AI-Based Job Matching & Ranking

**Status: 🔄 Implemented — Under Testing & Refinement**

The CV ranking system has been implemented and can evaluate candidate relevance against job descriptions.

The functionality is operational, but further improvements are required to enhance the accuracy and reliability of ranking results.

| Feature | Status |
|---------|--------|
| Initial CV ranking implementation | ✅ Completed |
| Integration with the processing pipeline | ✅ Completed |
| Job description-based candidate evaluation | ✅ Implemented |
| Testing and improving ranking accuracy | 🔄 In Progress |
| Refinement of relevance scoring | 🔄 In Progress |
| Final validation of ranking results | ⏳ Pending |

**Current Focus:** Improving the quality, consistency, and reliability of candidate relevance scores before finalizing the ranking system.

---

## Current Project Status

**Last Updated:** November 24, 2026

✅ **Completed:** Raw text extraction across all supported CV formats, including OCR.

✅ **Completed & Tested:** AI-based information extraction with structured JSON responses.

✅ **Implemented:** Three independently usable service modes for parsing, information extraction, and ranking.

🔄 **Under Refinement:** AI-based CV ranking against job descriptions.

🎯 **Next Focus:** Improve ranking accuracy, relevance scoring, and overall matching reliability.

---

## Installation & Usage

In `test_input.py`, choose **Add CVs** to process new documents or **Add saved CVs** to select entries from `output.xlsx`.

Enter a job description and select **Process & rank** to save ranked results to `ranking.xlsx`.

For installation, configuration, dependencies, and detailed usage instructions, see [how_to_use.md](how_to_use.md).
