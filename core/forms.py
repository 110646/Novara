from django import forms
from .models import Portfolio

MAJOR_CHOICES = [
    ('', 'Select Major'),  # Placeholder
    ('Accounting', 'Accounting'), ('Aerospace Engineering', 'Aerospace Engineering'),
    ('Agricultural Business and Management', 'Agricultural Business and Management'),
    ('Agricultural Economics', 'Agricultural Economics'), ('Agricultural Education', 'Agricultural Education'),
    ('Agricultural Journalism', 'Agricultural Journalism'), ('Agricultural Mechanization', 'Agricultural Mechanization'),
    ('Agriculture', 'Agriculture'), ('American History', 'American History'), ('American Literature', 'American Literature'),
    ('American Studies', 'American Studies'), ('Animal Science', 'Animal Science'), ('Anthropology', 'Anthropology'),
    ('Applied Mathematics', 'Applied Mathematics'), ('Aquatic Biology', 'Aquatic Biology'), ('Archaeology', 'Archaeology'),
    ('Architectural Engineering', 'Architectural Engineering'), ('Architecture', 'Architecture'), ('Art', 'Art'),
    ('Art Education', 'Art Education'), ('Art History', 'Art History'), ('Art Therapy', 'Art Therapy'), ('Astronomy', 'Astronomy'),
    ('Atmospheric Science', 'Atmospheric Science'), ('Aviation', 'Aviation'), ('Baking Science', 'Baking Science'),
    ('Biochemistry', 'Biochemistry'), ('Bioethics', 'Bioethics'), ('Biology', 'Biology'), ('Biomedical Engineering', 'Biomedical Engineering'),
    ('Biophysics', 'Biophysics'), ('Botany', 'Botany'), ('Business Administration', 'Business Administration'),
    ('Business Communications', 'Business Communications'), ('Business Education', 'Business Education'), ('Ceramic Engineering', 'Ceramic Engineering'),
    ('Ceramics', 'Ceramics'), ('Chemical Engineering', 'Chemical Engineering'), ('Chemical Physics', 'Chemical Physics'),
    ('Chemistry', 'Chemistry'), ('Child Development', 'Child Development'), ('Child Care', 'Child Care'),
    ('Civil Engineering', 'Civil Engineering'), ('Cognitive Psychology', 'Cognitive Psychology'), ('Comparative Literature', 'Comparative Literature'),
    ('Computer and Information Science', 'Computer and Information Science'), ('Computer Engineering', 'Computer Engineering'),
    ('Computer Graphics', 'Computer Graphics'), ('Computer Systems Analysis', 'Computer Systems Analysis'),
    ('Construction Management', 'Construction Management'), ('Creative Writing', 'Creative Writing'), ('Criminal Justice', 'Criminal Justice'),
    ('Criminology', 'Criminology'), ('Culinary Arts', 'Culinary Arts'), ('Dental Hygiene', 'Dental Hygiene'),
    ('Developmental Psychology', 'Developmental Psychology'), ('Diagnostic Medical Sonography', 'Diagnostic Medical Sonography'),
    ('Dietetics', 'Dietetics'), ('Digital Communications', 'Digital Communications'), ('Early Childhood Education', 'Early Childhood Education'),
    ('Economics', 'Economics'), ('Education', 'Education'), ('Educational Psychology', 'Educational Psychology'),
    ('Electrical Engineering', 'Electrical Engineering'), ('Engineering Mechanics', 'Engineering Mechanics'),
    ('Engineering Physics', 'Engineering Physics'), ('English Composition', 'English Composition'),
    ('English Literature', 'English Literature'), ('Entrepreneurship', 'Entrepreneurship'), ('Environmental Science', 'Environmental Science'),
    ('Epidemiology', 'Epidemiology'), ('Ethnic Studies', 'Ethnic Studies'), ('Experimental Psychology', 'Experimental Psychology'),
    ('Finance', 'Finance'), ('Food Science', 'Food Science'), ('Forensic Science', 'Forensic Science'), ('French', 'French'),
    ('Game Design', 'Game Design'), ('Genetics', 'Genetics'), ('Geography', 'Geography'), ('Geology', 'Geology'),
    ('Geophysics', 'Geophysics'), ('German', 'German'), ('Graphic Design', 'Graphic Design'), ('Health Administration', 'Health Administration'),
    ('Hebrew', 'Hebrew'), ('Historic Preservation', 'Historic Preservation'), ('History', 'History'),
    ('Home Economics', 'Home Economics'), ('Hospitality', 'Hospitality'), ('Human Communications', 'Human Communications'),
    ('Human Development', 'Human Development'), ('Industrial Design', 'Industrial Design'), ('Industrial Engineering', 'Industrial Engineering'),
    ('Industrial Management', 'Industrial Management'), ('Information Technology', 'Information Technology'),
    ('International Business', 'International Business'), ('International Relations', 'International Relations'),
    ('Italian', 'Italian'), ('Japanese', 'Japanese'), ('Jewish Studies', 'Jewish Studies'), ('Kinesiology', 'Kinesiology'),
    ('Latin American Studies', 'Latin American Studies'), ('Linguistics', 'Linguistics'), ('Management Information Systems', 'Management Information Systems'),
    ('Marketing', 'Marketing'), ('Mathematics', 'Mathematics'), ('Mechanical Engineering', 'Mechanical Engineering'),
    ('Medical Technology', 'Medical Technology'), ('Medieval and Renaissance Studies', 'Medieval and Renaissance Studies'),
    ('Microbiology', 'Microbiology'), ('Middle Eastern Studies', 'Middle Eastern Studies'), ('Military Science', 'Military Science'),
    ('Molecular Biology', 'Molecular Biology'), ('Molecular Genetics', 'Molecular Genetics'), ('Mortuary Science', 'Mortuary Science'),
    ('Music', 'Music'), ('Music Composition', 'Music Composition'), ('Music Education', 'Music Education'),
    ('Music History', 'Music History'), ('Music Performance', 'Music Performance'), ('Music Therapy', 'Music Therapy'),
    ('Native American Studies', 'Native American Studies'), ('Naval Architecture', 'Naval Architecture'),
    ('Neurobiology', 'Neurobiology'), ('Neuroscience', 'Neuroscience'), ('Nuclear Engineering', 'Nuclear Engineering'),
    ('Nursing', 'Nursing'), ('Nutrition', 'Nutrition'), ('Occupational Therapy', 'Occupational Therapy'),
    ('Oceanography', 'Oceanography'), ('Optometry', 'Optometry'), ('Organizational Behavior Studies', 'Organizational Behavior Studies'),
    ('Painting', 'Painting'), ('Paleontology', 'Paleontology'), ('Pastoral Studies', 'Pastoral Studies'),
    ('Petroleum Engineering', 'Petroleum Engineering'), ('Pharmacology', 'Pharmacology'), ('Pharmacy', 'Pharmacy'),
    ('Philosophy', 'Philosophy'), ('Photography', 'Photography'), ('Physical Education', 'Physical Education'),
    ('Physical Therapy', 'Physical Therapy'), ('Physics', 'Physics'), ('Physiology', 'Physiology'),
    ('Physiological Psychology', 'Physiological Psychology'), ('Planetary Science', 'Planetary Science'),
    ('Plant Pathology', 'Plant Pathology'), ('Plant Sciences', 'Plant Sciences'), ('Political Science', 'Political Science'),
    ('Portuguese', 'Portuguese'), ('Pre-Dentistry', 'Pre-Dentistry'), ('Pre-Law', 'Pre-Law'), ('Pre-Medicine', 'Pre-Medicine'),
    ('Pre-Optometry', 'Pre-Optometry'), ('Pre-Seminary', 'Pre-Seminary'), ('Pre-Veterinary', 'Pre-Veterinary'),
    ('Printmaking', 'Printmaking'), ('Product Design', 'Product Design'), ('Psychology', 'Psychology'),
    ('Public Administration', 'Public Administration'), ('Public Health', 'Public Health'), ('Public Policy Analysis', 'Public Policy Analysis'),
    ('Radiologic Technology', 'Radiologic Technology'), ('Radio and Television', 'Radio and Television'),
    ('Rehabilitation Services', 'Rehabilitation Services'), ('Religious Studies', 'Religious Studies'),
    ('Retailing', 'Retailing'), ('Russian', 'Russian'), ('Scandinavian Studies', 'Scandinavian Studies'),
    ('Slavic Languages and Literatures', 'Slavic Languages and Literatures'), ('Social Psychology', 'Social Psychology'),
    ('Social Work', 'Social Work'), ('Sociology', 'Sociology'), ('Soil Science', 'Soil Science'), ('South Asian Studies', 'South Asian Studies'),
    ('Spanish', 'Spanish'), ('Special Education', 'Special Education'), ('Speech Pathology', 'Speech Pathology'),
    ('Sports Management', 'Sports Management'), ('Statistics', 'Statistics'), ('Sustainable Resource Management', 'Sustainable Resource Management'),
    ('Theater', 'Theater'), ('Theology', 'Theology'), ('Toxicology', 'Toxicology'), ('Urban Planning', 'Urban Planning'),
    ('Urban Studies', 'Urban Studies'), ('Visual Communication', 'Visual Communication'), ('Visual Design', 'Visual Design'),
    ('Web Design', 'Web Design'), ('Web Management', 'Web Management'), ('Women\'s Studies', 'Women\'s Studies'),
    ('Zoology', 'Zoology'),
]

CLASS_YEAR_CHOICES = [
    ('', 'Select Academic Level'), 
    ('High School Student', 'High School Student'),
    ('Undergraduate Freshman', 'Undergraduate Freshman'),
    ('Undergraduate Sophomore', 'Undergraduate Sophomore'),
    ('Undergraduate Junior', 'Undergraduate Junior'),
    ('Undergraduate Senior', 'Undergraduate Senior'),
    ('Masters Student', 'Masters Student'),
    ('Doctoral Student', 'Doctoral Student'),
    ('Post-Graduate', 'Post-Graduate'),

]

US_UNIVERSITY_CHOICES = [
    ('', 'Select University'),
    ('Harvard University', 'Harvard University'),
    ('Stanford University', 'Stanford University'),
    ('Massachusetts Institute of Technology', 'Massachusetts Institute of Technology'),
    ('University of California, Berkeley', 'University of California, Berkeley'),
    ('California Institute of Technology', 'California Institute of Technology'),
    ('Princeton University', 'Princeton University'),
    ('Yale University', 'Yale University'),
    ('Columbia University', 'Columbia University'),
    ('University of Chicago', 'University of Chicago'),
    ('University of Pennsylvania', 'University of Pennsylvania'),
    ('Johns Hopkins University', 'Johns Hopkins University'),
    ('Duke University', 'Duke University'),
    ('Northwestern University', 'Northwestern University'),
    ('University of Michigan', 'University of Michigan'),
    ('Cornell University', 'Cornell University'),
    ('New York University', 'New York University'),
    ('University of California, Los Angeles', 'University of California, Los Angeles'),
    ('University of Washington', 'University of Washington'),
    ('University of Wisconsin-Madison', 'University of Wisconsin-Madison'),
    ('University of Texas at Austin', 'University of Texas at Austin'),
    ('University of North Carolina at Chapel Hill', 'University of North Carolina at Chapel Hill'),
    ('Carnegie Mellon University', 'Carnegie Mellon University'),
    ('Brown University', 'Brown University'),
    ('Boston University', 'Boston University'),
    ('University of California, San Diego', 'University of California, San Diego'),
    ('University of Illinois at Urbana-Champaign', 'University of Illinois at Urbana-Champaign'),
    ('University of Florida', 'University of Florida'),
    ('University of Southern California', 'University of Southern California'),
    ('Ohio State University', 'Ohio State University'),
    ('Pennsylvania State University', 'Pennsylvania State University'),
    # ... add more as needed ...
]

class PortfolioForm(forms.ModelForm):
    name = forms.CharField(max_length=255, required=True, label="Name")
    major = forms.ChoiceField(choices=MAJOR_CHOICES, required=True, label="Major")
    class_year = forms.ChoiceField(choices=CLASS_YEAR_CHOICES, required=True, label="Academic Level")
    university = forms.ChoiceField(choices=US_UNIVERSITY_CHOICES, required=True, label="University")
    research_interests = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'e.g., Machine Learning, Computer Vision, AI'}), required=True, label="Research Interests")

    class Meta:
        model = Portfolio
        fields = ['name', 'major', 'class_year', 'university', 'research_interests', 'resume']

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Resume file size must not exceed 5MB.")
            if not resume.name.endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
        return resume
