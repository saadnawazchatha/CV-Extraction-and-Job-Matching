
# CV Project — CV Data Extraction & AI-Based Job Matching

## 1. Project Overview

This project is a Python-based microservice designed to extract structured information from CVs and eventually match candidates against job descriptions using AI-based techniques.

The project was initiated to overcome the limitations of traditional CV data extraction systems that rely primarily on **Regular Expressions (Regex)**.

While Regex can identify information using predefined patterns, it has limitations when dealing with:

- Different CV layouts and formatting styles.
- Unstructured or inconsistently organized information.
- Contextual understanding of professional experience and qualifications.
- Variations in how candidate information is presented.

The goal is to develop a more flexible CV processing and candidate matching system capable of understanding resume content and evaluating its relevance to specific job requirements.

---

## 2. Project Objectives

The project aims to achieve the following:

1. Accept CVs in multiple document formats.
2. Extract raw textual information from uploaded CVs.
3. Process scanned and image-based documents using OCR.
4. Identify and extract meaningful candidate information.
5. Convert the extracted information into a structured JSON response.
6. Accept job descriptions for candidate evaluation.
7. Use AI-based techniques to match candidate profiles against job requirements.
8. Return candidate matching results based on their relevance to the job description.

**Current Development Focus:** Document processing and raw text extraction.

---

## 3. Supported Input Formats

The microservice is designed to process CVs uploaded in the following formats:

| File Format | Processing Method | Development Status |
|-------------|-------------------|--------------------|
| Word Document (Text-Based) | Direct text extraction | ✅ Completed |
| PDF (Text-Based) | Direct text extraction | ✅ Completed |
| Image | Optical Character Recognition (OCR) | ✅ Completed |
| Scanned PDF | PDF-to-image conversion followed by OCR | ✅ Completed |
| Word Document (Image-Based) | Embedded image extraction followed by OCR | 🔄 In Progress |

Each document format is handled using dedicated parsers to keep the processing pipeline modular and maintainable.

---

## 4. Project Workflow

The overall project workflow is divided into multiple stages.

### Stage 1: Document Upload

A CV is uploaded to the Python microservice.

The uploaded document may be:

- A Word document containing selectable text.
- A text-based PDF document.
- An image containing CV information.
- A scanned PDF containing image-based pages.
- A Word document containing an embedded image of a CV.

### Stage 2: Raw Data Extraction

The microservice determines the appropriate processing method based on the uploaded document format.

**Word Documents:**

Text is extracted directly from Word documents containing readable text.

For Word documents containing embedded images of CVs, additional OCR-based processing is required. This functionality is currently under development.

**Text-Based PDFs:**

Text is extracted directly from PDF documents containing selectable text.

**Images:**

Optical Character Recognition (OCR) is used to recognize text inside uploaded images and convert it into raw textual information.

**Scanned PDFs:**

Since scanned PDFs contain image-based content rather than selectable text, their pages are converted into images.

These images are then processed using OCR to extract the textual information.

### Current Output

At the current development stage, the microservice returns:

- The filename of the uploaded CV.
- The raw text extracted from the uploaded document.

**Important:** The extracted text is currently returned in its raw form. Structured candidate information extraction has not yet been implemented.

---

### Stage 3: Structured Information Extraction (Planned)

Once raw text extraction is completed, the extracted content will be passed to dedicated information extractors.

These extractors will identify and organize meaningful candidate information.

The target information includes:

- Candidate Name
- Email Address
- Phone Number
- Location
- Professional Summary
- Technical and Professional Skills
- Work Experience
- Educational Qualifications
- Languages

The extracted information will then be converted into a structured JSON response.

The system will also need to handle missing information without generating fabricated candidate details.

---

### Stage 4: AI-Based Job Description Matching (Planned)

After structured candidate information extraction is implemented, the microservice will be extended to process job descriptions.

AI-based techniques will be used to analyze candidate profiles and compare them against the requirements specified in job descriptions.

The matching system aims to evaluate factors such as:

- Required skills and candidate skills.
- Relevant professional experience.
- Educational qualifications.
- Technical expertise.
- Overall relevance to job requirements.

The objective is to identify candidates whose profiles most closely align with the given job description.

---

### Stage 5: Candidate Ranking (Future Development)

The system will eventually support evaluating multiple CVs against a given job description.

Candidate matching results may include relevance scores and ranking information.

However, the following aspects have not yet been finalized:

- Candidate scoring methodology.
- Ranking criteria and weighting.
- Result ordering.
- Final matching response format.

These components will be designed and implemented during the job matching phase.

---

## 5. Expected Structured JSON Output

The following JSON illustrates the **planned response structure** after the structured information extraction stage is implemented.

**Note:** This is an example of the intended future output and does not represent the current functionality.

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

The JSON structure may evolve as additional extraction capabilities are implemented.

---

## 6. Development Progress

This section tracks the implementation status of the major project components.

### Phase 1: Document Processing & Raw Text Extraction

**Overall Status: Mostly Completed**

| Status | Feature |
|--------|---------|
| ✅ Completed | Establish project structure with dedicated document parsers |
| ✅ Completed | Implement text extraction from Word documents |
| ✅ Completed | Implement text extraction from text-based PDFs |
| ✅ Completed | Implement OCR-based text extraction from images |
| ✅ Completed | Implement scanned PDF processing |
| ✅ Completed | Convert scanned PDF pages into images for OCR |
| ✅ Completed | Return uploaded CV filename and extracted raw text |
| 🔄 In Progress | Support Word documents containing embedded images of CVs |

---

### Phase 2: Structured CV Information Extraction

**Overall Status: Planned**

| Status | Feature |
|--------|---------|
| ⏳ Planned | Develop candidate information extractors |
| ⏳ Planned | Extract candidate names and contact details |
| ⏳ Planned | Extract professional summaries |
| ⏳ Planned | Extract technical and professional skills |
| ⏳ Planned | Extract work experience |
| ⏳ Planned | Extract educational qualifications |
| ⏳ Planned | Extract language information |
| ⏳ Planned | Generate structured JSON responses |
| ⏳ Planned | Handle missing or unavailable candidate information |

---

### Phase 3: AI-Based Job Description Matching

**Overall Status: Planned**

| Status | Feature |
|--------|---------|
| ⏳ Planned | Accept job descriptions as input |
| ⏳ Planned | Identify relevant requirements from job descriptions |
| ⏳ Planned | Compare candidate profiles against job requirements |
| ⏳ Planned | Implement AI-based candidate matching |
| ⏳ Planned | Design candidate relevance scoring methodology |
| ⏳ Planned | Define the final matching response format |
| ⏳ Planned | Support candidate ranking based on job relevance |

---

## 7. Current Development Status

**Last Updated: November 19, 2026**

### ✅ Completed Work

The document processing stage currently supports raw text extraction from the following document types:

**1. Word Documents**

Successfully implemented raw text extraction from Word documents containing selectable text.

**2. Text-Based PDF Documents**

Successfully implemented direct text extraction from PDF documents containing readable text.

**3. Image-Based CVs**

Successfully integrated Optical Character Recognition (OCR) for recognizing and extracting text from uploaded CV images.

**4. Scanned PDF Documents**

Successfully implemented a processing mechanism that converts scanned PDF pages into images before passing them to OCR for text recognition.

**5. Raw Text Response**

The microservice currently returns the uploaded CV filename along with the extracted raw text.

These completed components establish the foundation for structured candidate information extraction.

---

### 🔄 Work in Progress

**OCR Processing for Image-Based Word Documents**

Currently working on Word documents where the CV content exists as an embedded image rather than selectable text.

The implementation aims to:

1. Identify image-based content inside Word documents.
2. Extract embedded CV images.
3. Process the extracted images using OCR.
4. Return the recognized text as part of the raw text response.

Once completed, the microservice will support raw text extraction from all currently targeted document formats.

---

### ⏳ Next Development Steps

**Immediate Next Steps:**

1. Complete OCR support for image-based Word documents.
2. Finalize the document processing stage.
3. Begin developing structured candidate information extractors.
4. Extract relevant candidate fields from raw CV text.
5. Generate structured JSON responses containing candidate information.

**Future Development:**

1. Implement job description processing.
2. Research and implement suitable AI-based matching techniques.
3. Develop candidate-to-job relevance evaluation.
4. Design a candidate scoring and ranking system.
5. Finalize the API response structure for job matching results.

---

## 8. Documentation

Detailed instructions for installing dependencies, configuring the development environment, and running the microservice are available in the project documentation.

**Installation and Usage Guide:**

[HOW_TO_USE.md](HOW_TO_USE.md)

---

## 9. Project Status

**Current Status: Active Development**

The project is currently in the **Document Processing and Raw Text Extraction** phase.

The following components have been successfully implemented:

- Word document text extraction.
- Text-based PDF extraction.
- OCR-based image text extraction.
- Scanned PDF processing using OCR.
- Raw text responses containing uploaded CV filenames.

**Currently Under Development:**

- OCR support for embedded images inside Word documents.

**Planned Development:**

- Structured candidate information extraction.
- AI-based CV and job description matching.
- Candidate relevance scoring and ranking.

The project will continue to evolve as each development phase is completed.
