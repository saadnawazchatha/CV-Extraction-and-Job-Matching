
# CV Project — CV Data Extraction & AI-Based Job Matching

## Project Overview

A Python-based microservice developed to overcome the limitations of traditional Regex-based CV extraction.

The project extracts raw text from CVs, processes it using an AI-based information extraction model, and generates structured candidate information in JSON format.

The system also includes an initial CV ranking implementation that evaluates candidate relevance against job descriptions.

## Project Workflow

1. **Document Upload:** Accept CVs in PDF, Word, and image formats.
2. **Raw Text Extraction:** Extract text using dedicated document parsers and OCR where required.
3. **AI Information Extraction:** Process raw text using an AI model to identify relevant candidate information.
4. **JSON Response:** Generate structured candidate information in a standardized JSON format.
5. **AI-Based Job Matching:** Compare candidate information against job descriptions to evaluate and rank CVs by relevance.

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
| Improve extraction accuracy and text structure | ✅ Completed |

The extraction pipeline has been refined to provide more accurate, structured, and readable raw text for downstream AI processing.

---

### Phase 2 — Structured Information Extraction

**Status: 🔄 Implemented — Under Testing**

An AI-based information extraction model has been integrated into the processing pipeline.

Once a CV has been parsed, the raw text is passed to the AI model, which extracts relevant candidate information and generates a structured JSON response.

The extracted information includes:

- **Personal Details:** Name, email, phone, and location.
- **Professional Profiles:** LinkedIn and GitHub.
- **Professional Information:** Summary and skills.
- **Work Experience:** Job title, company, employment period, and highlights.
- **Education:** Degree, institution, and graduation year.

#### Desired JSON Response

Example of the expected output using fictional candidate information:

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

#### Current Testing

The AI extraction model is being tested to ensure:

- Extracted information accurately matches the original CV.
- JSON responses consistently follow the desired structure.
- Missing information is represented using `null` or empty arrays.
- Incorrect or fabricated information is minimized.
- Different CV layouts produce reliable extraction results.

**The model is implemented, but extraction accuracy and JSON response quality are still being evaluated and refined.**

---

### Phase 3 — AI-Based Job Matching & Ranking

**Status: 🔄 Initial Implementation — Under Development**

The first stage of the CV ranking system has been implemented.

This introduces the foundation for evaluating candidate information against job descriptions and determining how relevant a CV is to a particular job.

#### Current Progress

| Feature | Status |
|---------|--------|
| Initial CV ranking implementation | ✅ Implemented |
| Integration of ranking functionality into the microservice | ✅ Implemented |
| Refinement of job description matching | 🔄 In Progress |
| Improvement and validation of ranking results | 🔄 In Progress |
| Finalization of scoring and ranking methodology | ⏳ Planned |

#### Next Steps

- Refine the comparison between candidate profiles and job requirements.
- Improve the relevance and reliability of ranking results.
- Evaluate the effectiveness of the scoring methodology.
- Test the ranking system using different CVs and job descriptions.
- Finalize the matching and ranking process.

**Note:** The ranking system is currently in its initial development stage. Its scoring methodology, accuracy, and final output format have not yet been finalized.

---

## Current Project Status

**Last Updated:** November 23, 2026

✅ **Completed:** Raw text extraction from PDF, Word, and image-based CVs, including OCR processing and extraction quality improvements.

🔄 **Under Testing:** AI-based information extraction model that converts raw CV text into structured candidate JSON responses.

🔄 **Under Development:** Initial AI-based CV ranking system for evaluating candidate relevance against job descriptions.

⏳ **Next Focus:** Improve and validate information extraction accuracy, job description matching, and candidate ranking results.

---

## Installation & Usage

In `test_input.py`, choose **Add CVs** for new files or **Add saved CVs** for entries in `output.xlsx`. Enter a job description and use **Process & rank** to append the ranked results to `ranking.xlsx`.

For installation, dependencies, and instructions on running the project, see [how_to_use.md](how_to_use.md).
