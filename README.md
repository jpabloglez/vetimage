# VetImage

VetImage is a comprehensive DICOM imaging platform for veterinary practice. It provides advanced tools for managing, viewing, and analyzing animal patient imaging — including CT, MRI, X-ray, ultrasound, and other DICOM-compliant modalities — organized around the real-world Owner → Animal Patient → Study workflow.

## Overview

VetImage is designed to streamline veterinary imaging workflows by providing:
- **Owner & Patient Registry**: Structured Owner → Animal Patient → Study hierarchy with species, breed, microchip ID, and owner contact — multi-pet households supported from day one
- **DICOM Storage & Management**: Upload, organize, and retrieve studies with complete metadata preservation
- **Advanced Viewer Integration**: Built-in OHIF viewer integration and Cornerstone.js support for high-quality image visualization
- **AI-Assisted Analysis**: Pluggable connector architecture (REST or gRPC) for radiology decision support with real-time status via WebSocket
- **Image Annotations**: Rich annotation system with automatic measurement calculations (distance, area, angles)
- **Structured Reports**: Generate vetted radiology reports from AI findings with PDF export
- **RESTful API**: Comprehensive REST API for integration with practice management and other systems

## Disclaimer

This application is intended for veterinary decision support, education, research, and development purposes. It is not a substitute for professional clinical judgement. All imaging analysis and interpretation must be performed by qualified veterinary professionals.

The developers and contributors are not responsible for any clinical decisions, misuse, or misinterpretation of data processed through this system. This platform must be used in compliance with all applicable data protection regulations (e.g. GDPR) and local veterinary practice requirements.

## Features

### Core Functionality
- **DICOM Upload & Storage**: Support for all DICOM-compliant imaging formats
- **Metadata Management**: Complete DICOM tag extraction and JSON storage
- **Multi-Modality Support**: CT, MRI, X-ray, CR, ultrasound, and other imaging modalities
- **OHIF Viewer**: Integrated image viewer with advanced visualization tools
- **Cornerstone.js Integration**: High-performance image rendering

### Advanced Features
- **AI Analysis Pipeline**: Pluggable connectors (REST+webhook or gRPC) dispatch studies to model services; findings stream back to the viewer and pre-fill draft reports — all human-in-the-loop. See [docs/AI-WORKFLOW.md](docs/AI-WORKFLOW.md); try it with `make ai-demo`.
- **Owner & Animal Patient Records**: Multi-pet owners, species/breed, microchip, and weight tracking
- **Image Annotations**: 10+ annotation types (rectangle, ellipse, polygon, ruler, angle, arrow, etc.)
- **Automatic Measurements**: Server-side calculation for distance (mm/pixels), area, and angles
- **Thumbnail System**: Lazy-loaded thumbnails in small (100px), medium (200px), and large (400px) sizes
- **Advanced Search**: Multi-criteria search by patient name, study description, date ranges, and modality
- **Saved Searches**: Store and reuse frequently used search queries
- **User Management**: Authentication and authorization with JWT tokens
- **Storage Quotas**: Per-user storage limits and tracking

## Technologies

### Backend
- Python 3.x
- Django 4.1+
- Django REST Framework 3.14+
- PostgreSQL 12+
- pydicom 2.4.4 (DICOM processing)
- Pillow 10.1.0 (Image processing)
- JWT Authentication

### Frontend
- React
- TypeScript
- OHIF Viewer
- Cornerstone.js
- Tailwind CSS

### Infrastructure
- Docker & Docker Compose
- Nginx (production)
- Git

## Prerequisites

- Docker Desktop or Docker Engine (20.10+)
- Docker Compose (1.29+)
- Git
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space minimum

## Getting Started

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/vetimage.git
   cd vetimage
   ```

2. Start the application:
   ```bash
   docker-compose up -d --build
   ```

3. Access the application:
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:3081
   - API Documentation: http://localhost:3081/api/docs

### Using Make Commands

The project includes a comprehensive Makefile for easy management:

```bash
# Show all available commands
make help

# Start development environment
make dev

# View logs
make logs

# Access backend shell
make shell-backend

# Run migrations
make migrate

# Run tests
make test

# Register veterinary AI models
make models-seed

# Run the AI analysis pipeline end-to-end against the reference service
make ai-demo

# Stop all services
make down
```

For a complete list of Make commands, run `make help` or see the Makefile.

### Production deployment

The base `docker-compose.yml` is development-oriented. For production, apply the
override and follow the checklist in **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

It enforces `DEBUG=False`, a strong `SECRET_KEY` (the app refuses to boot in
production with the insecure dev key), HTTPS-only cookies + HSTS, runs
migrations + `collectstatic`, and serves static assets via WhiteNoise.

## Project Structure

```
vetimage/
├── app/
│   ├── backend/          # Django backend application
│   │   ├── dicom_images/ # DICOM management app
│   │   ├── ai_analysis/  # AI model registry, task dispatch, connectors, webhooks
│   │   ├── patients/     # Veterinary registry, clinical records, portal, messaging
│   │   ├── reports/      # Structured reports + PDF export
│   │   ├── core/         # Core Django settings
│   │   └── manage.py     # Django management script
│   ├── frontend/         # React frontend application
│   └── services/         # In-repo model services (e.g. vet-thorax reference fixture)
├── compose/              # Docker configuration files
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── data/                 # Persistent data
│   ├── db/              # PostgreSQL data
│   └── media/           # Uploaded DICOM files
├── docs/                # Detailed documentation
│   ├── AI-WORKFLOW.md            # AI analysis pipeline (dispatch→webhook→findings→report)
│   ├── DEPLOYMENT.md             # Production deployment guide + checklist
│   ├── VETERINARY_ALIGNMENT_REPORT.md
│   ├── PENDING_FEATURES.md
│   └── models/MIRAGE-INTEGRATION.md
├── setup/               # Setup scripts and requirements
├── docker-compose.yml   # Docker services configuration
├── Makefile            # Management commands
└── README.md           # This file
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db-vetimage
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Storage
MEDIA_ROOT=/var/www/app/backend/media
MEDIA_URL=/media/

# JWT
JWT_SECRET_KEY=your-jwt-secret-here
```

### Database Setup

After starting the containers for the first time:

```bash
# Run migrations
make migrate

# Create superuser (optional)
make shell-backend
python manage.py createsuperuser
```

## API Documentation

The platform provides a comprehensive REST API. Key endpoints include:

### Studies & Series
- `GET /api/studies/` - List all studies
- `POST /api/studies/upload/` - Upload DICOM files
- `GET /api/series/{uid}/` - Get series details
- `GET /api/series/{uid}/thumbnail/{size}/` - Get thumbnail

### Search
- `POST /api/search/advanced/` - Advanced multi-criteria search
- `GET /api/search/saved/` - List saved searches
- `POST /api/search/saved/` - Create saved search

### Annotations
- `GET /api/images/{uid}/annotations/` - List image annotations
- `POST /api/images/{uid}/annotations/` - Create annotation
- `PUT /api/annotations/{id}/` - Update annotation

For complete API documentation with examples, see [docs/API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md).

## Usage Examples

### Upload DICOM Files

```bash
curl -X POST http://localhost:3081/api/studies/upload/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "files=@/path/to/dicom/file.dcm"
```

### Search Studies

```bash
curl -X POST http://localhost:3081/api/search/advanced/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Rex",
    "modality": "CT",
    "start_date": "2024-01-01"
  }'
```

### Create Annotation

```bash
curl -X POST http://localhost:3081/api/images/{image_uid}/annotations/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "annotation_type": "ruler",
    "geometry_data": {
      "points": [[100, 100], [200, 200]]
    },
    "label": "Lesion measurement"
  }'
```

## Testing

### Run All Tests

```bash
# Backend tests
make test-backend

# Frontend tests
make test-frontend

# All tests with coverage
make test-coverage
```

### Manual Testing

For detailed testing instructions, see [docs/TESTING-GUIDE.md](docs/TESTING-GUIDE.md).

## Development

### Backend Development

```bash
# Access backend shell
make shell-backend

# Install new dependencies
pip install package-name
pip freeze > requirements.txt

# Create migrations
make makemigrations

# Apply migrations
make migrate
```

### Frontend Development

```bash
# Access frontend shell
make shell-frontend

# Install dependencies
npm install package-name

# Run development server
npm run dev
```

## Deployment

### Production Recommendations

1. **Database**: Switch to PostgreSQL with proper backups
2. **Storage**: Configure S3 or Azure Blob Storage for DICOM files
3. **Security**: Enable HTTPS, configure CORS, implement rate limiting
4. **Performance**: Set up CDN for thumbnails, enable caching
5. **Monitoring**: Implement logging and monitoring solutions

For detailed deployment instructions, see [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md).

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Technical overview and architecture
- **[DICOM_ENHANCEMENTS.md](docs/DICOM_ENHANCEMENTS.md)** - Detailed feature documentation
- **[API_QUICK_REFERENCE.md](docs/API_QUICK_REFERENCE.md)** - API endpoint reference
- **[OHIF-INTEGRATION-COMPLETE.md](docs/OHIF-INTEGRATION-COMPLETE.md)** - OHIF viewer integration guide
- **[TESTING-GUIDE.md](docs/TESTING-GUIDE.md)** - Testing procedures and examples

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the documentation in `/docs`
- Run `make help` for available commands

## Acknowledgments

- **OHIF**: Open source medical imaging viewer
- **Cornerstone.js**: Medical image rendering library
- **pydicom**: Python DICOM library
- **Django REST Framework**: Web API framework

---

**Status**: Active Development
**Version**: 1.0.0
**Last Updated**: December 2024
