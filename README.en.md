# AILearn Hub

> AI-Powered Learning System Based on Ebbinghaus Forgetting Curve

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

## 📖 Overview

AILearn Hub is a modern intelligent learning platform that helps users master knowledge efficiently through scientific learning algorithms. The system integrates multiple learning modes including practice, exams, and review, making it ideal for certification exam preparation and skill enhancement.

### ✨ Key Features

- **🧠 Intelligent Review Scheduling**
  - 9-stage review algorithm based on Ebbinghaus forgetting curve
  - Automatically schedules optimal review times to reinforce memory
  - Dynamic adjustment: advance on correct answers, regress on incorrect ones

- **📝 Flexible Learning Modes**
  - **Practice Mode**: Batch-based practice with real-time feedback, skip questions supported
  - **Exam Mode**: Simulates real exam environment, supports fixed question sets and dynamic randomization
  - **Review Mode**: Intelligently recommends questions for review, targets weak areas
  - **Mistake Book**: Automatically records mistakes, supports one-click retry

- **📊 Comprehensive Learning Statistics** *[WIP]*
  - Multi-dimensional data: accuracy rate, study time, mastery level
  - Course progress tracking with visual progress display
  - Mistake analysis to identify knowledge gaps
  > ⚠️ Note: Learning statistics module is under development, some features may be incomplete

- **🎯 Multi-Course & Multi-Question Set Support**
  - Flexible course management system
  - Supports custom question sets (regular sets and fixed exam sets)
  - Advanced features: difficulty grading, knowledge point tagging

- **📥 Convenient Data Import**
  - Support for Markdown format question bank import
  - Support for Word document import (with red answer marking)
  - Automatic conversion to standard JSON format
  - Complete data validation and conversion reports

- **🔧 Developer Friendly**
  - Dev mode for quick experience without registration
  - Complete RESTful API documentation
  - One-click Docker deployment
  - Frontend-backend separation architecture

## 🏗️ Tech Stack

### Backend

- **FastAPI**: Modern, high-performance web framework
  - Auto-generated OpenAPI documentation
  - Type validation (Pydantic)
  - Async support
- **SQLAlchemy**: Python ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **Python**: 3.11+

### Frontend

- **Next.js 16**: React framework (App Router)
  - Server-side rendering (SSR)
  - Automatic code splitting
  - File-system routing
- **React 19**: UI library
- **TypeScript**: Type safety
- **Tailwind CSS 4**: Rapid UI development
- **KaTeX**: Math formula rendering

### Data Import Tools

- **Python**: Script development language
- **uv**: Fast Python package manager
- **python-docx**: Word document parsing
- **Markdown**: Standard text format support

## 📁 Project Structure

```
aie55_llm5_learnhub/
├── src/
│   ├── backend/                 # Backend service (FastAPI)
│   │   ├── main.py             # Application entry point
│   │   ├── app/
│   │   │   ├── core/           # Core modules (database, Ebbinghaus algorithm)
│   │   │   ├── models/         # Data models
│   │   │   ├── services/       # Business logic
│   │   │   └── api/            # API routes
│   │   ├── data/               # Database files
│   │   └── Dockerfile
│   │
│   └── frontend/               # Frontend application (Next.js)
│       ├── app/                # Pages directory
│       │   ├── page.tsx        # Home page
│       │   ├── quiz/           # Practice page
│       │   ├── exam/           # Exam page
│       │   ├── mistakes/       # Mistakes page
│       │   ├── stats/          # Statistics page
│       │   └── courses/        # Courses page
│       ├── components/         # Reusable components
│       ├── lib/                # Utility libraries (API Client)
│       └── Dockerfile
│
├── scripts/                    # Data import scripts
│   ├── init_db.py             # Initialize database
│   ├── init_course_data.py    # Initialize course data
│   ├── import_questions.py    # Import questions
│   ├── convert_md_to_json.py  # Markdown to JSON converter
│   ├── convert_docx_to_json.py # Word to JSON converter
│   └── data/
│       ├── input/              # Input data sources
│       └── output/             # Converted JSON files
│
├── schema.sql                  # Database schema definition
├── docker-compose.yml          # Docker Compose configuration
├── SCRIPT_MANUAL.md           # Script usage manual
└── README.md                  # Project documentation
```

## 🚀 Quick Start

> ⚠️ **Important**: You must run the database initialization scripts before starting the application!
> See the "Initialize Data" section below for detailed steps.

### Option 1: Docker Deployment (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/aie55_llm5_learnhub.git
cd aie55_llm5_learnhub

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Option 2: Local Development

#### 1. Start Backend

```bash
# Navigate to backend directory
cd src/backend

# Install dependencies (uv is recommended for faster installation)
pip install -r requirements.txt
# Or use: uv sync

# Start development server
uvicorn main:app --host 0.0.0.0 --reload --port 8000
```

Backend will start at `http://localhost:8000`

#### 2. Start Frontend

```bash
# Navigate to frontend directory
cd src/frontend

# Install dependencies
npm install

# Configure environment variables (create .env.local)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

Frontend will start at `http://localhost:3000`

#### 3. Initialize Data

```bash
# Navigate to scripts directory
cd scripts

# Install dependencies
uv sync

# Initialize database
uv run python init_db.py

# Create default courses
uv run python init_course_data.py

# Import questions (optional)
uv run python import_questions.py data/output/sampleQuiz.json --course-code ai_cert_exam
```

For detailed script usage, see: [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md)

## 🎯 Features

### Ebbinghaus Forgetting Curve

The system implements a scientific memory reinforcement algorithm that automatically schedules reviews based on the Ebbinghaus forgetting curve:

| Stage | Interval | Description |
|-------|----------|-------------|
| Stage 0 | New Question | First learning |
| Stage 1 | 30 minutes later | Short-term memory reinforcement |
| Stage 2 | 12 hours later | Mid-term memory consolidation |
| Stage 3 | 1 day later | Long-term memory begins to form |
| Stage 4 | 2 days later | Memory stability improves |
| Stage 5 | 4 days later | Memory continues to reinforce |
| Stage 6 | 7 days later | One-week review milestone |
| Stage 7 | 15 days later | Long-term memory established |
| Stage 8 | - | Mastered, no review needed |

**Rules**:
- Correct answer: Advance to next stage
- Incorrect answer: Return to stage 1

### Practice Mode

- **Batch Practice**: Extract a group of questions each time (default: 10)
- **Immediate Feedback**: Unified scoring after batch completion, view detailed explanations
- **Flexible Control**: Support skipping questions, arrange your own pace
- **Progress Tracking**: Record answer status and review stage for each question

### Exam Mode

- **Real Simulation**: Fully simulate exam environment, no answers shown during the exam
- **Multiple Modes**:
  - Fixed question set: Questions presented in preset order
  - Dynamic randomization: Randomly select based on difficulty, question type, etc.
- **Score Analysis**: Provide detailed score report after exam completion

### Mistake Book

- **Automatic Recording**: Incorrect answers automatically added to mistake book
- **Mistake Statistics**: Multi-dimensional analysis by course, question type, difficulty
- **One-click Retry**: Support batch retry of mistakes for targeted reinforcement

### Learning Statistics *[WIP]*

> ⚠️ This module is under development and features may be incomplete.

- **Overall Overview**: Total questions answered, accuracy rate, mastered questions
- **Progress Tracking**: Course learning progress, questions pending review
- **Trend Analysis**: Study time distribution, score change curves

## 📥 Data Import

The system supports multiple question bank formats. For detailed instructions, see [SCRIPT_MANUAL.md](SCRIPT_MANUAL.md).

### Markdown Format

```bash
# Convert Markdown to JSON
cd scripts
uv run python convert_md_to_json.py -f sampleQuiz.md

# Import to database
uv run python import_questions.py \
  data/output/sampleQuiz.json \
  --course-code ai_cert_exam
```

### Word Document Format

```bash
# Convert Word to JSON (must mark correct answers in red)
uv run python convert_docx_to_json.py -i data/input/exam_questions.docx

# Import as fixed question set
uv run python import_questions.py \
  data/output/exam_questions.json \
  --course-code ai_cert_exam \
  --question-set-code exam_set1 \
  --question-set-name "2025 Mock Exam Set"
```

## 🔌 API Documentation

After starting the backend service, visit the following addresses for complete API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main API Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| User Management | `/api/users` | User creation, query, statistics |
| Course Management | `/api/courses` | Course list, details |
| Question Set Management | `/api/question-sets` | Question set list, question query |
| Practice Mode | `/api/quiz` | Batch practice, submit answers |
| Exam Mode | `/api/exam` | Start exam, submit answers |
| Review Scheduling | `/api/review` | Get review questions, submit answers |
| Mistake Management | `/api/mistakes` | Mistake list, retry mistakes |

## 🛠️ Development Guide

### Adding New Features

**Backend**:

1. Create data models in `app/models/`
2. Implement business logic in `app/services/`
3. Create API routes in `app/api/`
4. Register routes in `main.py`

**Frontend**:

1. Create new pages in `app/`
2. Create reusable components in `components/`
3. Add API methods in `lib/api.ts`
4. Style with Tailwind CSS

### Environment Variables

**Backend** (`.env`):

```env
DATABASE_URL=sqlite:///./data/app.db
SECRET_KEY=your-secret-key-change-me
DEV_MODE=true
```

**Frontend** (`.env.local`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📚 Documentation

- [Backend Development Guide](src/backend/README.md) - Backend architecture, API design, development guide
- [Frontend Development Guide](src/frontend/README.md) - Frontend architecture, component design, style guide
- [Script Usage Manual](SCRIPT_MANUAL.md) - Data import, format conversion, initialization process

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues, fork the repository, and create pull requests.

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE) for details.

> **Note**: The AGPL license requires that if you run a modified version of this software on a network, you must provide the source code to users of the network.

## 🙏 Acknowledgments

Thanks to all developers who contributed to this project!

---

**Start Your Learning Journey**: [Visit Online Demo](http://localhost:3000) or [Local Deployment](#quick-start)

For questions, please submit an [Issue](https://github.com/yourusername/aie55_llm5_learnhub/issues) or contact the maintainers.
