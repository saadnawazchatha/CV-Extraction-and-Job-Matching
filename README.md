
# CV Project — CV Data Extraction & Job Matching

## 1. Project Overview

This project is a Python-based microservice designed to extract structured information from CVs and eventually match candidates against job descriptions using AI-based techniques.

The project was initiated to overcome the limitations of traditional CV data extraction systems that rely primarily on Regular Expressions (Regex).

While Regex can identify information based on predefined patterns, it has limitations when dealing with varying CV formats, unstructured information, and contextual understanding.

The goal of this project is to develop a more flexible CV processing and candidate matching system that can understand resume content and evaluate its relevance to specific job requirements.

---

## 2. Project Objectives

The project aims to achieve the following:

1. Accept CVs in multiple file formats.
2. Extract raw text from uploaded documents.
3. Process scanned and image-based documents using OCR.
4. Extract useful candidate information from the raw text.
5. Convert extracted information into a structured JSON response.
6. Accept job descriptions and analyze their requirements.
7. Use AI-based methods to match candidate CVs against job descriptions.
8. Return candidate matching results based on their relevance to the job.

**Current Focus:** Document processing and raw text extraction.

---

## 3. Supported Input Formats

The microservice is designed to process CVs uploaded in the following formats:

| File Type | Processing Method | Status |
|-----------|-------------------|--------|
| Word Document | Direct text extraction | Completed |
| PDF (Text-based) | Direct text extraction | Completed |
| Image | Optical Character Recognition (OCR) | Completed |
| Scanned PDF | PDF to image conversion followed by OCR | Completed |
| Image-based Word Document | Image extraction and OCR | In Progress |

The system handles different document formats using dedicated parsers.

---

## 4. Project Workflow

The overall workflow is divided into multiple stages.

### Stage 1: Document Upload

A CV is uploaded to the Python microservice.

The uploaded document may be:

- A Word document
- A PDF containing selectable text
- A scanned PDF
- An image containing CV information
- A Word document containing an embedded image of a CV

### Stage 2: Raw Data Extraction

The appropriate parser processes the uploaded document.

**Word Documents:**
Extract text directly from the document. Image-based content inside Word documents requires additional OCR processing.

**Text-based PDFs:**
Extract text directly from the PDF.

**Images:**
Use Optical Character Recognition (OCR) to recognize and extract text.

**Scanned PDFs:**
Convert PDF pages into images and pass them through OCR to extract readable text.

At this stage, the microservice returns the uploaded CV's filename along with the extracted raw text.

### Stage 3: Structured Information Extraction (Planned)

The extracted raw text will be passed to information extractors that identify relevant candidate details.

Target fields include:

- Name
- Email address
- Phone number
- Location
- Professional summary
- Technical and professional skills
- Work experience
- Educational qualifications
- Languages

The extracted information will then be converted into a structured JSON response.

### Stage 4: Job Description Matching (Planned)

Once structured CV data extraction has been implemented, the microservice will be extended to accept job descriptions.

AI-based techniques will be used to compare candidate information against job requirements.

The objective is to identify candidates whose qualifications, experience, and skills are most relevant to a given job description.

### Stage 5: Candidate Ranking (Future Development)

The system will eventually return matching results for multiple CVs.

The exact scoring methodology, ranking order, and final response structure have not yet been determined.

These will be designed during the matching phase of development.

---

## 5. Expected Structured JSON Output

The following is an example of the **planned** JSON structure after the information extraction stage has been implemented.

**Note:** This is an illustrative target response, not the current microservice output.

```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": "+1 555 123 4567",
  "location": "Berlin, Germany",
  "summary": "Senior backend engineer with 8+ years of experience.",
  "skills": [
    "Python",
    "FastAPI",
    "PostgreSQL",
    "Docker"
  ],
  "experience": [
    {
      "title": "Senior Backend Engineer",
      "company": "TechCorp",
      "period": "2020 - Present",
      "highlights": [
        "Led migration to microservices architecture."
      ]
    }
  ],
  "education": [
    {
      "degree": "MSc Computer Science",
      "school": "TU Berlin",
      "year": 2016
    }
  ],
  "languages": [
    "English (C1)",
    "German (B2)"
  ]
}
```

The final output structure may evolve as development progresses.

---

## 6. Development Progress

### Phase 1: Document Processing & Raw Text Extraction

**Status: Mostly Completed**

- [x] Establish project structure with dedicated document parsers.
- [x] Implement text extraction from Word documents.
- [x] Implement text extraction from text-based PDFs.
- [x] Implement OCR-based text extraction from images.
- [x] Implement scanned PDF processing.
- [x] Convert scanned PDF pages into images for OCR.
- [x] Return uploaded CV filename and extracted raw text.
- [ ] Support Word documents containing embedded images of CVs.

### Phase 2: Structured CV Information Extraction

**Status: Planned**

- [ ] Develop extractors for candidate information.
- [ ] Extract personal and contact details.
- [ ] Extract professional summaries.
- [ ] Extract technical and professional skills.
- [ ] Extract work experience.
- [ ] Extract educational qualifications.
- [ ] Extract language information.
- [ ] Generate structured JSON responses.
- [ ] Handle missing or unavailable candidate information.

### Phase 3: AI-Based Job Description Matching

**Status: Planned**

- [ ] Accept job descriptions as input.
- [ ] Identify relevant requirements from job descriptions.
- [ ] Compare candidate profiles against job requirements.
- [ ] Implement AI-based candidate matching.
- [ ] Design a candidate relevance scoring methodology.
- [ ] Define the final matching response format.
- [ ] Support candidate ranking based on job relevance.

---

## 7. Current Development Status

**Last Updated: November 19, 2026**

### Completed Work

The document processing stage currently supports raw text extraction from:

- Word documents containing text.
- Text-based PDF documents.
- Images using OCR.
- Scanned PDF documents using PDF-to-image conversion and OCR.

The microservice currently returns the uploaded filename along with the raw text extracted from the document.

This establishes the foundation for the next development stage, where raw text will be processed into meaningful candidate information.

### Work in Progress

**OCR Processing for Image-Based Word Documents**

Currently working on handling Word documents where CV content is embedded as an image rather than stored as selectable text.

The objective is to identify and extract the embedded image content, process it through OCR, and return the recognized text.

### Next Development Steps

1. Complete support for image-based Word documents.
2. Begin implementing structured candidate information extractors.
3. Transform raw CV text into meaningful JSON fields.
4. Prepare the extracted information for future AI-based job matching.

---

## 8. Documentation

For instructions on installing dependencies, setting up the environment, and running the project, refer to:

[HOW_TO_USE.md](HOW_TO_USE.md)

---

## 9. Project Status

**Active Development**

The project is currently in its document processing and text extraction phase.

Structured information extraction, AI-based job matching, and candidate ranking will be implemented in subsequent development phases.
