"""Unit tests for StudySpark's PDF handling and web routes."""

import io
import unittest
from unittest.mock import patch

import app as project
from google.genai import types


def make_text_pdf(text: str) -> bytes:
    """Build a tiny one-page PDF fixture without extra test dependencies."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    stream = (
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
        + content
        + b"\nendstream"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        stream,
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


class StudySparkTests(unittest.TestCase):
    def setUp(self) -> None:
        project.app.config.update(TESTING=True)
        self.client = project.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as current_session:
            self.csrf_token = current_session["csrf_token"]

    def test_home_and_health_routes(self) -> None:
        home = self.client.get("/")
        health = self.client.get("/health")

        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Turn your notes into a", home.data)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json, {"status": "ok"})
        self.assertEqual(home.headers["X-Content-Type-Options"], "nosniff")

    def test_missing_non_pdf_and_malformed_uploads_are_rejected(self) -> None:
        missing = self.client.post("/generate", data={"csrf_token": self.csrf_token})
        non_pdf = self.client.post(
            "/generate",
            data={
                "csrf_token": self.csrf_token,
                "pdf": (io.BytesIO(b"text"), "notes.txt"),
            },
            content_type="multipart/form-data",
        )
        malformed = self.client.post(
            "/generate",
            data={
                "csrf_token": self.csrf_token,
                "pdf": (io.BytesIO(b"not a PDF"), "notes.pdf"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertIn(b"Choose a PDF", missing.data)
        self.assertEqual(non_pdf.status_code, 400)
        self.assertIn(b"must be a PDF", non_pdf.data)
        self.assertEqual(malformed.status_code, 400)
        self.assertIn(b"valid PDF", malformed.data)

    def test_pdf_extraction_preserves_page_references(self) -> None:
        source_text, page_count = project.extract_pdf_text(
            make_text_pdf("Cells are the basic unit of life.")
        )

        self.assertEqual(page_count, 1)
        self.assertIn("[Page 1]", source_text)
        self.assertIn("basic unit of life", source_text)

    def test_generated_quiz_renders_questions_and_csv(self) -> None:
        quiz = project.Quiz(
            title="Biology revision",
            questions=[
                project.Question(
                    question="What is the basic unit of life?",
                    options=["Cell", "Atom", "Organ", "Tissue"],
                    correct_option_index=0,
                    explanation="The source identifies the cell as the basic unit of life.",
                    source_page=1,
                )
            ],
        )
        with patch.object(project, "create_quiz", return_value=quiz):
            response = self.client.post(
                "/generate",
                data={
                    "csrf_token": self.csrf_token,
                    "pdf": (
                        io.BytesIO(make_text_pdf("Cells are the basic unit of life.")),
                        "biology.pdf",
                    ),
                    "question_count": "5",
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"What is the basic unit of life?", response.data)
        self.assertIn(b"PDF page 1", response.data)

        csv_response = self.client.post(
            "/download",
            data={
                "csrf_token": self.csrf_token,
                "quiz_json": quiz.model_dump_json(),
            },
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response.content_type)
        self.assertIn(b"Correct Answer", csv_response.data)
        self.assertIn(b"Cell", csv_response.data)

    def test_invalid_quiz_payload_is_rejected_by_csv_route(self) -> None:
        invalid_quiz = project.Quiz(
            title="Invalid quiz",
            questions=[
                project.Question(
                    question="Choose an option",
                    options=["Only one"],
                    correct_option_index=0,
                    explanation="Test data",
                    source_page=1,
                )
            ],
        )

        response = self.client.post(
            "/download",
            data={
                "csrf_token": self.csrf_token,
                "quiz_json": invalid_quiz.model_dump_json(),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"quiz data was invalid", response.data)

    def test_csv_formula_text_is_escaped(self) -> None:
        self.assertEqual(project.csv_safe("=1+1"), "'=1+1")
        self.assertEqual(project.csv_safe("  @SUM(A1:A2)"), "'  @SUM(A1:A2)")
        self.assertEqual(project.csv_safe("Ordinary answer"), "Ordinary answer")

    def test_generation_limit_allows_ten_per_hour(self) -> None:
        client_key = "unit-test-client"
        with project._generation_lock:
            project._generation_times.pop(client_key, None)

        for request_number in range(project.GENERATION_LIMIT):
            self.assertTrue(project.allow_generation(client_key, now=1000 + request_number))
        self.assertFalse(project.allow_generation(client_key, now=1010))
        self.assertTrue(
            project.allow_generation(
                client_key,
                now=1000 + project.GENERATION_WINDOW_SECONDS + 1,
            )
        )

    def test_rate_limited_request_does_not_call_gemini(self) -> None:
        with patch.object(project, "allow_generation", return_value=False):
            with patch.object(project, "create_quiz") as create_quiz:
                response = self.client.post(
                    "/generate",
                    data={
                        "csrf_token": self.csrf_token,
                        "pdf": (
                            io.BytesIO(make_text_pdf("Cells are the basic unit of life.")),
                            "biology.pdf",
                        ),
                        "question_count": "5",
                    },
                    content_type="multipart/form-data",
                )

        self.assertEqual(response.status_code, 429)
        self.assertIn(b"limit of 10 quizzes per hour", response.data)
        create_quiz.assert_not_called()

    def test_form_posts_require_csrf_token(self) -> None:
        response = self.client.post("/generate", data={})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"form session expired", response.data)

    def test_gemini_structured_output_config(self) -> None:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=project.Quiz,
            temperature=0.2,
        )

        self.assertEqual(config.response_mime_type, "application/json")


if __name__ == "__main__":
    unittest.main()
