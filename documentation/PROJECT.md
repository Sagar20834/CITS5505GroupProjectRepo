# RoadWatch – Perth
## Community Road Issue Reporting System

## Overview
**RoadWatch Perth** is a web application that allows users to report road-related issues such as potholes, damaged roads, and unsafe road conditions, either anonymously or by providing their username.

The platform also enables users to view issues reported by others, helping to increase community awareness and reduce duplicate reports. The goal of the application is to help road authorities quickly identify problem areas and respond to them more efficiently.

## Target Users
- Residents of Perth
- Local commuters:
  - Pedestrians
  - Drivers
  - Cyclists
- Local authorities monitoring road conditions

## Functionalities

### 1. User Authentication
- Create an account
- Log in
- Log out

### 2. Report Road Issues
Users can submit reports containing:
- Type of issue
- Location of issue
- Description of issue
- Option to report anonymously

### 3. View Reports
Users can:
- View reported road issues
- See the description and location of each issue
- Identify areas with frequent issues

### 4. Personal Reports
Logged-in users can:
- View the issues they have reported
- Check the status of their reported issues

### 5. Data Persistence
- All user and report data is stored in a database
- Data remains available across sessions


## System Pages

The RoadWatch Perth system consists of the following main pages:

1. **Home Page (`index.html`)**
   - Displays the application title
   - Provides navigation buttons for:
     - Viewing reports
     - Adding a new report

2. **Register Page (`register.html`)**
   - Allows a new user to create an account
   - Contains:
     - Email input field
     - Password input field
     - Register button

3. **Login Page (`login.html`)**
   - Allows registered users to log in
   - Contains:
     - Email/username input field
     - Password input field
     - Login button

4. **View Reports Page (`reports.html`)**
   - Displays a list of submitted road issue reports
   - Each report shows:
     - Location
     - Description
     - Issue type
     - Status

5. **Add Report Page (`report.html`)**
   - Allows users to submit a road issue
   - Contains:
     - Issue type field
     - Description field
     - Submit button
     - Anonymous reporting option

6. **Admin Dashboard Page (`dashboard.html`)**
   - Allows administrators to manage the system
   - Displays:
     - List of user-posted reports
     - Graphs and pie charts for report analysis

7. **Report Details Page (`report_details.html`)**
   - Displays complete information for a selected report
   - Includes:
     - Full description
     - Location
     - Status
     - Reporter name or anonymous label