# 🚀 Quick Start Testing Guide

## Step 1: Rebuild Docker
```powershell
cd c:\Users\Lenovo\Documents\Project\WEB
docker-compose up --build
```

Wait for all services to start:
- ✅ postgres: "database system is ready to accept connections"
- ✅ backend: "Running on http://0.0.0.0:5000"
- ✅ frontend: "Listening server"

**Time to wait:** ~30-60 seconds

---

## Step 2: Open Application

1. Open browser: **http://localhost:3000**
2. See: Auth page loading
3. Check console: Should see green checkmarks ✅

---

## Step 3: Open DevTools

**Press:** `F12`  
**Go to:** "Console" tab

You should see:
```
🔧 [auth.js] API_BASE configured: http://localhost:5000
✅ [auth.js] register-form element found
✅ [auth.js] Register form event listener attached successfully
```

---

## Step 4: Test Registration

### Fill Form (Student Role)
- **Full Name:** Nguyễn Văn A
- **MSSV:** 20230001
- **Email:** nguyenvana@student.edu.vn
- **Password:** Password123
- **Confirm Password:** Password123

### Click Register Button
- Watch console for colored output
- Watch toast for blue message

---

## Step 5: Monitor Console Output

### Expected Sequence (Green Checkmarks ✅):

1. **Immediate:**  
   `🔵 FORM SUBMIT EVENT FIRED`

2. **Prevention:**  
   `✅ preventDefault() called - page will not refresh`

3. **Form Processing:**  
   `📋 [auth.js] Role selected: student`

4. **Validation:**  
   ```
   ✅ Email is valid: nguyenvana@student.edu.vn
   ✅ ALL VALIDATION PASSED
   ```

5. **Payload:**  
   ```
   📤 REQUEST PAYLOAD
   (table shows: email, password, full_name, role, mssv, etc.)
   ✅ All required fields present
   ```

6. **Fetch:**  
   ```
   📡 FETCH CONFIGURATION
   [auth.js] URL: http://localhost:5000/api/auth/register
   [auth.js] Method: POST
   [auth.js] Headers: { Content-Type: application/json }
   ```

7. **Sending:**  
   `⏳ SENDING FETCH REQUEST...`

8. **Response:**  
   ```
   📥 RESPONSE RECEIVED
   [auth.js] Status: 201 Created
   [auth.js] OK: true
   ✅ REGISTRATION SUCCESSFUL
   ```

9. **Redirect:**  
   `[auth.js] Redirecting to dashboard...`

---

## Step 6: Check Network Tab

1. Click: **Network** tab in DevTools
2. Fill and click register again
3. Look for: **POST request** to `/api/auth/register`
4. Expected status: **201** ✅

Click on request → **Response** tab:
```json
{
  "message": "User registered successfully",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "nguyenvana@student.edu.vn",
    "full_name": "Nguyễn Văn A",
    "role": "student"
  }
}
```

---

## Step 7: Verify Backend Logs

In terminal where docker-compose is running, look for:

```
backend | 🔵 [REGISTRATION] Email: nguyenvana@student.edu.vn
backend | 🔵 USER OBJECT BEFORE COMMIT: ...
backend | 🟢 ✅ COMMIT SUCCESSFUL
backend | 🟢 ✅ VERIFICATION QUERY PASSED
backend | 🟢 Response will return 201 with user object
```

---

## Step 8: Check Database

Open Adminer: **http://localhost:8080**

1. Login:
   - System: PostgreSQL
   - Server: postgres
   - Username: postgres
   - Password: (from docker-compose.yml)
   - Database: smartmatch

2. Click: **users** table
3. Look for: Your registered email
4. Verify: `skill_vector` is NOT NULL, `full_name` is correct

---

## 🔍 If Something Goes Wrong

### Symptom: No console output at all
**Cause:** Event listener not attached  
**Solution:** Check browser console for `register-form element found` message  
**Fix:** Make sure form ID is `register-form` in HTML

### Symptom: Console output but no Network request
**Cause:** preventDefault() not working or form fields invalid  
**Solution:** Look for ❌ in validation logs  
**Fix:** Fill all required fields before submitting

### Symptom: Network request but 404 status
**Cause:** Backend endpoint doesn't exist or wrong URL  
**Solution:** Check backend logs for route registration  
**Fix:** Verify `/api/auth/register` route exists in app.py

### Symptom: Network request but 500 status  
**Cause:** Backend error during registration  
**Solution:** Check backend error logs for detailed traceback  
**Fix:** Run `docker-compose logs backend` and look for 🔴 errors

### Symptom: 201 response but no redirect
**Cause:** localStorage might have issues or redirect failed  
**Solution:** Check if localStorage has 'token', 'sm_user', 'sm_role'  
**Fix:** Check if dashboard.html exists and is accessible

---

## 📋 Testing Checklist

- [ ] Docker-compose started successfully
- [ ] http://localhost:3000 loads without errors
- [ ] DevTools console shows API_BASE configured
- [ ] DevTools console shows form element found and listener attached
- [ ] Fill registration form completely
- [ ] Click register button
- [ ] Console shows 🔵 FORM SUBMIT EVENT FIRED
- [ ] Console shows 📋 Role selected: student (or lecturer)
- [ ] Console shows ✅ ALL VALIDATION PASSED
- [ ] Console shows 📤 REQUEST PAYLOAD (with table)
- [ ] Console shows 📡 FETCH CONFIGURATION (with URL/method/headers)
- [ ] Console shows ⏳ SENDING FETCH REQUEST...
- [ ] Network tab shows POST /api/auth/register request appearing
- [ ] Network response shows Status 201
- [ ] Console shows 📥 RESPONSE RECEIVED with status 201
- [ ] Console shows ✅ REGISTRATION SUCCESSFUL
- [ ] Toast shows green "Đăng ký thành công!" message
- [ ] Page redirects to dashboard.html
- [ ] Backend logs show 🟢 ✅ COMMIT SUCCESSFUL
- [ ] Database shows new user in users table with correct data
- [ ] skill_vector is NOT NULL and has 384-dim vector
- [ ] localStorage contains token, sm_user, sm_role (check in DevTools → Storage → Local Storage)

---

## 🆘 Still Having Issues?

### Check Files Modified:
All fixes are in these files:
- ✅ `/backend/app.py` - Lines 475-640 (registration route)
- ✅ `/frontend/public/auth.js` - Multiple sections (API_BASE, showToast, form handler)
- ✅ `/frontend/public/auth.css` - Toast styles
- ✅ `/frontend/public/auth.html` - Form structure (verify form id)

### Check Documentation:
- `FRONTEND_EVENT_DEBUGGING_GUIDE.md` - Comprehensive debugging guide
- `FRONTEND_CODE_COMPARISON.md` - Before/after code comparison
- `API_DOCUMENTATION.md` - API endpoint details

### View Full Backend Logs:
```powershell
docker-compose logs backend -f
```
Replace `backend` with `postgres` to see database logs, or `frontend` for frontend logs.

### Restart Everything:
```powershell
docker-compose down
docker-compose up --build
```

---

## 📞 Common Test Scenarios

### Scenario 1: Successful Registration
```
Email: test@student.edu.vn
Password: Password123
Role: Student
Expected: 201 response, redirect to dashboard
```

### Scenario 2: Duplicate Email
```
Email: (same as previously registered)
Expected: 409 Conflict, error message shown
```

### Scenario 3: Weak Password
```
Password: 123 (too short)
Expected: Validation error in console, toast shows message
```

### Scenario 4: Email Mismatch
```
Email: invalid-email (no @ symbol)
Expected: ❌ Email validation failed in console
```

---

**Version:** 1.0  
**Last Updated:** March 21, 2024  
**Status:** Ready for Testing
