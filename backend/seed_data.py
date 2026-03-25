import uuid
from datetime import datetime, timedelta
from app import db, User, Project, Application, VerifiedSkill
from werkzeug.security import generate_password_hash

def seed_database():
    print("🌱 Seeding database with sample data...")
    
    # Clear existing data
    db.session.query(VerifiedSkill).delete()
    db.session.query(Application).delete()
    db.session.query(Project).delete()
    db.session.query(User).delete()
    db.session.commit()
    
    # Create sample students
    students = [
        {
            'email': 'student1@dut.edu.vn',
            'name': 'Nguyễn Văn A',
            'student_id': '102250001',
            'faculty': 'Công nghệ thông tin',
            'skills': ['Python', 'Machine Learning', 'Data Analysis', 'TensorFlow', 'SQL'],
            'research_interests': ['AI', 'Data Science', 'Computer Vision'],
            'gpa': 3.5,
            'year_of_study': 3
        },
        {
            'email': 'student2@dut.edu.vn',
            'name': 'Trần Thị B',
            'student_id': '102250002',
            'faculty': 'Công nghệ thông tin',
            'skills': ['Java', 'Web Development', 'Spring Boot', 'React', 'MySQL'],
            'research_interests': ['Web Development', 'Software Engineering', 'Cloud Computing'],
            'gpa': 3.7,
            'year_of_study': 4
        },
        {
            'email': 'student3@dut.edu.vn',
            'name': 'Lê Văn C',
            'student_id': '102250003',
            'faculty': 'Điện tử viễn thông',
            'skills': ['C++', 'Embedded Systems', 'IoT', 'Python', 'Linux'],
            'research_interests': ['IoT', 'Embedded Systems', 'Robotics'],
            'gpa': 3.2,
            'year_of_study': 3
        }
    ]
    
    # Create sample lecturers
    lecturers = [
        {
            'email': 'lecturer1@dut.edu.vn',
            'name': 'PGS.TS. Trần Văn D',
            'position': 'Phó Giáo sư',
            'department': 'Công nghệ thông tin',
            'research_fields': ['AI', 'Machine Learning', 'Computer Vision']
        },
        {
            'email': 'lecturer2@dut.edu.vn',
            'name': 'TS. Nguyễn Thị E',
            'position': 'Giảng viên chính',
            'department': 'Hệ thống thông tin',
            'research_fields': ['Web Development', 'Cloud Computing', 'Big Data']
        },
        {
            'email': 'lecturer3@dut.edu.vn',
            'name': 'ThS. Lê Văn F',
            'position': 'Giảng viên',
            'department': 'Điện tử viễn thông',
            'research_fields': ['IoT', 'Embedded Systems', 'Robotics']
        }
    ]
    
    created_users = {}
    
    # Create student users
    for i, student_data in enumerate(students, 1):
        user = User(
            id=uuid.uuid4(),
            email=student_data['email'],
            password_hash=generate_password_hash('student123'),
            name=student_data['name'],
            role='student',
            student_id=student_data['student_id'],
            faculty=student_data['faculty'],
            skills=student_data['skills'],
            research_interests=student_data['research_interests'],
            gpa=student_data['gpa'],
            year_of_study=student_data['year_of_study'],
            is_verified=True,
            is_active=True
        )
        db.session.add(user)
        created_users[f'student{i}'] = user
    
    # Create lecturer users
    for i, lecturer_data in enumerate(lecturers, 1):
        user = User(
            id=uuid.uuid4(),
            email=lecturer_data['email'],
            password_hash=generate_password_hash('lecturer123'),
            name=lecturer_data['name'],
            role='lecturer',
            position=lecturer_data['position'],
            department=lecturer_data['department'],
            research_fields=lecturer_data['research_fields'],
            is_verified=True,
            is_active=True
        )
        db.session.add(user)
        created_users[f'lecturer{i}'] = user
    
    db.session.commit()
    print(f"✅ Created {len(students)} students and {len(lecturers)} lecturers")
    
    # Create sample projects
    projects = [
        {
            'title': 'Nghiên cứu ứng dụng AI trong chẩn đoán hình ảnh y tế',
            'description': 'Phát triển hệ thống AI hỗ trợ bác sĩ chẩn đoán các bệnh qua hình ảnh X-quang, MRI.',
            'research_field': 'AI & Y tế',
            'required_skills': ['Python', 'Machine Learning', 'Deep Learning', 'Computer Vision'],
            'preferred_skills': ['TensorFlow', 'PyTorch', 'Medical Imaging'],
            'difficulty_level': 'high',
            'duration_weeks': 24,
            'max_students': 2,
            'lecturer': created_users['lecturer1']
        },
        {
            'title': 'Xây dựng hệ thống quản lý thư viện thông minh sử dụng IoT',
            'description': 'Phát triển hệ thống quản lý sách tự động với RFID, hệ thống đề xuất sách thông minh.',
            'research_field': 'IoT & Hệ thống thông minh',
            'required_skills': ['Python', 'IoT', 'Web Development', 'Database'],
            'preferred_skills': ['Django', 'React', 'RFID', 'Cloud Computing'],
            'difficulty_level': 'medium',
            'duration_weeks': 16,
            'max_students': 3,
            'lecturer': created_users['lecturer2']
        },
        {
            'title': 'Phân tích cảm xúc người dùng trên mạng xã hội sử dụng NLP',
            'description': 'Xây dựng mô hình phân tích cảm xúc từ bình luận trên Facebook, Twitter.',
            'research_field': 'NLP & Xử lý ngôn ngữ tự nhiên',
            'required_skills': ['Python', 'NLP', 'Machine Learning', 'Data Analysis'],
            'preferred_skills': ['Transformers', 'BERT', 'Sentiment Analysis'],
            'difficulty_level': 'medium',
            'duration_weeks': 20,
            'max_students': 2,
            'lecturer': created_users['lecturer1']
        },
        {
            'title': 'Hệ thống giám sát môi trường sử dụng cảm biến IoT',
            'description': 'Phát triển hệ thống thu thập và phân tích dữ liệu môi trường thời gian thực.',
            'research_field': 'IoT & Môi trường',
            'required_skills': ['C++', 'Embedded Systems', 'IoT', 'Python'],
            'preferred_skills': ['Arduino', 'Raspberry Pi', 'Sensor Networks'],
            'difficulty_level': 'medium',
            'duration_weeks': 18,
            'max_students': 2,
            'lecturer': created_users['lecturer3']
        }
    ]
    
    created_projects = []
    for i, project_data in enumerate(projects, 1):
        project = Project(
            id=uuid.uuid4(),
            title=project_data['title'],
            description=project_data['description'],
            research_field=project_data['research_field'],
            required_skills=project_data['required_skills'],
            preferred_skills=project_data['preferred_skills'],
            difficulty_level=project_data['difficulty_level'],
            duration_weeks=project_data['duration_weeks'],
            max_students=project_data['max_students'],
            lecturer_id=project_data['lecturer'].id,
            status='open',
            created_at=datetime.utcnow() - timedelta(days=i*7),
            deadline=datetime.utcnow() + timedelta(days=30 + i*7),
            is_public=True
        )
        db.session.add(project)
        created_projects.append(project)
    
    db.session.commit()
    print(f"✅ Created {len(projects)} research projects")
    
    # Create sample applications with AI matching scores
    applications = [
        {'student': created_users['student1'], 'project': created_projects[0], 'score': 85.5},
        {'student': created_users['student2'], 'project': created_projects[0], 'score': 72.3},
        {'student': created_users['student1'], 'project': created_projects[1], 'score': 68.7},
        {'student': created_users['student3'], 'project': created_projects[1], 'score': 91.2},
        {'student': created_users['student2'], 'project': created_projects[2], 'score': 88.9},
        {'student': created_users['student3'], 'project': created_projects[3], 'score': 94.5},
    ]
    
    for i, app_data in enumerate(applications):
        application = Application(
            id=uuid.uuid4(),
            student_id=app_data['student'].id,
            project_id=app_data['project'].id,
            match_score=app_data['score'],
            match_details={
                'base_similarity': app_data['score'] * 0.9,
                'required_skills_match': 95 if i % 2 == 0 else 75,
                'preferred_skills_match': 80 if i % 3 == 0 else 60,
                'final_score': app_data['score']
            },
            application_text=f'Tôi rất quan tâm đến đề tài này vì phù hợp với định hướng nghiên cứu của tôi.',
            status='pending' if i < 3 else 'accepted' if i < 5 else 'reviewed',
            applied_at=datetime.utcnow() - timedelta(days=i*2)
        )
        db.session.add(application)
    
    db.session.commit()
    print(f"✅ Created {len(applications)} applications with AI matching scores")
    
    # Create verified skills
    verified_skills = [
        {'student': created_users['student1'], 'skill': 'Python', 'level': 'advanced'},
        {'student': created_users['student1'], 'skill': 'Machine Learning', 'level': 'intermediate'},
        {'student': created_users['student2'], 'skill': 'Web Development', 'level': 'advanced'},
        {'student': created_users['student2'], 'skill': 'React', 'level': 'intermediate'},
        {'student': created_users['student3'], 'skill': 'IoT', 'level': 'advanced'},
        {'student': created_users['student3'], 'skill': 'Embedded Systems', 'level': 'intermediate'},
    ]
    
    for skill_data in verified_skills:
        verified_skill = VerifiedSkill(
            id=uuid.uuid4(),
            student_id=skill_data['student'].id,
            skill=skill_data['skill'],
            verified_by=created_users['lecturer1'].id,
            project_id=created_projects[0].id,
            level=skill_data['level'],
            evidence='Hoàn thành dự án nghiên cứu xuất sắc',
            verification_date=datetime.utcnow() - timedelta(days=30)
        )
        db.session.add(verified_skill)
    
    db.session.commit()
    print(f"✅ Created {len(verified_skills)} verified skills")
    
    print("=" * 60)
    print("🌱 SEEDING COMPLETE!")
    print("=" * 60)
    print("Sample Login Credentials:")
    print("Students: student1@dut.edu.vn / student123")
    print("Lecturers: lecturer1@dut.edu.vn / lecturer123")
    print("=" * 60)

if __name__ == '__main__':
    from app import app
    with app.app_context():
        seed_database()
        