/* ═══════════════════════════════════════════════════════════════════
   DAWATRACK · script.js  v5 — FULLY BACKEND-CONNECTED
   Every data operation calls the FastAPI backend. Nothing except the
   JWT token and a small cached-user object lives in localStorage.

   Sections in this file (search these markers to jump around):
     [A] API CORE
     [B] SESSION / AUTH HELPERS
     [C] UTILITIES (pure frontend — unchanged from before)
     [D] TOAST
     [E] PORTAL — login / register
     [F] DOCTOR PICKER (NEW — patient selects their doctor)
     [G] PATIENT DASHBOARD INIT
     [H] MEDICATION LOGGING (+ optional schedule creation)
     [I] SCHEDULES TAB (NEW — interval-based reminders)
     [J] SMS LOG (NEW — session view of send-now results)
     [K] CAREGIVERS
     [L] MEDICINE REQUESTS (pharmacy bridge — stays localStorage, see note)
     [M] PHARMACY MESSAGES (stays localStorage, see note)
     [N] CARE FEED (doctor notes)
     [O] PATIENT CHART
     [P] DOCTOR DASHBOARD
     [Q] GLOBAL INIT

   Anywhere a call depends on a backend route that does not exist yet,
   it is marked:   // 🆕 NEEDS BACKEND — see chat notes
═══════════════════════════════════════════════════════════════════ */

/* ═══ [A] API CORE ═══════════════════════════════════════════════ */
const isLocalFrontend = ["localhost", "127.0.0.1"].includes(
  window.location.hostname,
);
const API = isLocalFrontend ? "http://localhost:8000" : window.location.origin;

function getToken() {
  return localStorage.getItem("dt_token");
}
function setToken(t) {
  localStorage.setItem("dt_token", t);
}
function clearToken() {
  localStorage.removeItem("dt_token");
}

function getCachedUser() {
  try {
    return JSON.parse(localStorage.getItem("dt_user"));
  } catch {
    return null;
  }
}
function setCachedUser(u) {
  localStorage.setItem("dt_user", JSON.stringify(u));
}
function clearCachedUser() {
  localStorage.removeItem("dt_user");
}

/**
 * Central fetch wrapper. Throws Error(message) on any non-2xx response
 * so callers can just try/catch and show the message in a toast.
 */
async function api(method, path, body, auth = true) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = "Bearer " + t;
  }
  const res = await fetch(API + path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }

  if (!res.ok) {
    let msg = "Request failed.";
    if (data?.detail) {
      msg = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg).join(", ")
        : data.detail;
    }
    throw new Error(msg);
  }
  return data;
}

/* ═══ [B] SESSION / AUTH HELPERS ════════════════════════════════ */
function getSession() {
  const u = getCachedUser();
  const t = getToken();
  if (!u || !t) return null;
  return {
    id: u.id,
    role: u.role,
    name: u.name,
    email: u.email,
    phone: u.phone || "",
    doctor_id: u.doctor_id || null,
  };
}

function requireRole(role) {
  const s = getSession();
  if (!s || s.role !== role) window.location.href = "portal.html";
}

function handleLogout() {
  clearToken();
  clearCachedUser();
  window.location.href = "portal.html";
}
window.handleLogout = handleLogout;

/* Refresh the cached user from the backend (call after any profile change) */
async function refreshMe() {
  // GET /auth/me — already used earlier for PATCH; assumed to also support GET.
  const me = await api("GET", "/auth/me");
  setCachedUser(me);
  return me;
}

/* ═══ [C] UTILITIES — pure frontend, no backend involvement ═══════ */
function adherenceRate(logs) {
  if (!logs.length) return 0;
  return Math.round((logs.filter((l) => l.taken).length / logs.length) * 100);
}
function fmtDate(str) {
  if (!str) return "—";
  return new Date(str + "T00:00:00").toLocaleDateString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
function fmtTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr),
    h = d.getHours(),
    m = d.getMinutes().toString().padStart(2, "0");
  return `${h % 12 || 12}:${m} ${h >= 12 ? "pm" : "am"}`;
}
function timeAgo(iso) {
  const d = (Date.now() - new Date(iso)) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return Math.floor(d / 60) + "m ago";
  if (d < 86400) return Math.floor(d / 3600) + "h ago";
  return Math.floor(d / 86400) + "d ago";
}
function dosesPerDay(hrs) {
  return Math.round(24 / hrs);
}
function relLabel(r) {
  const m = {
    me: "Me (self)",
    spouse: "Spouse",
    partner: "Partner",
    parent: "Parent",
    sibling: "Sibling",
    child: "Child",
    relative: "Relative",
    caregiver: "Caregiver",
    friend: "Friend",
  };
  return m[r] || r;
}
function badgeAdherence(rate) {
  if (rate >= 80) return `<span class="badge badge-green">✓ ${rate}%</span>`;
  if (rate >= 50) return `<span class="badge badge-amber">⚠ ${rate}%</span>`;
  return `<span class="badge badge-red">✗ ${rate}%</span>`;
}
function riskBadge(rate) {
  if (rate >= 80) return '<span class="badge badge-green">Low Risk</span>';
  if (rate >= 50) return '<span class="badge badge-amber">Medium Risk</span>';
  return '<span class="badge badge-red">High Risk</span>';
}
function noteTypeStyle(type) {
  switch (type) {
    case "praise":
      return {
        icon: "🌟",
        bg: "#EDF5F2",
        border: "#9DD1C2",
        accentBg: "#5DAC96",
        label: "Great news",
        labelColor: "#2E7A65",
      };
    case "reminder":
      return {
        icon: "🔔",
        bg: "#FBF5E6",
        border: "#F0CC88",
        accentBg: "#D98A2A",
        label: "Reminder",
        labelColor: "#A0620A",
      };
    case "urgent":
      return {
        icon: "⚠️",
        bg: "#FAF0F0",
        border: "#F0AAAA",
        accentBg: "#D94F4F",
        label: "Urgent",
        labelColor: "#B03030",
      };
    case "advice":
      return {
        icon: "💊",
        bg: "#EAF3FA",
        border: "#9DD0F0",
        accentBg: "#3A8DC4",
        label: "Advice",
        labelColor: "#1A6496",
      };
    case "pharmacy":
      return {
        icon: "🏪",
        bg: "#EDF5F2",
        border: "#9DD1C2",
        accentBg: "#5DAC96",
        label: "Pharmacy",
        labelColor: "#2E7A65",
      };
    default:
      return {
        icon: "📋",
        bg: "#F4F8F7",
        border: "#D1E4DE",
        accentBg: "#1B5271",
        label: "Note",
        labelColor: "#1B5271",
      };
  }
}
function dosesUpcomingLocal(schedule, count) {
  const doses = [];
  const start = new Date(
    schedule.start_date + "T" + (schedule.first_dose_time || "08:00") + ":00",
  );
  const end = new Date(schedule.end_date + "T23:59:59");
  const hrsMs = schedule.interval_hours * 3600000;
  let cur = new Date(start);
  while (cur <= end && doses.length < count) {
    doses.push(new Date(cur));
    cur = new Date(cur.getTime() + hrsMs);
  }
  return doses;
}

/* ═══ [D] TOAST ══════════════════════════════════════════════════ */
function showToast(msg, type = "success") {
  let c = document.querySelector(".toast-container");
  if (!c) {
    c = document.createElement("div");
    c.className = "toast-container";
    document.body.appendChild(c);
  }
  const t = document.createElement("div");
  t.className = `toast-item ${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "✗" : "ℹ";
  const clr =
    type === "success" ? "#2DAF83" : type === "error" ? "#D94F4F" : "#3A8DC4";
  t.innerHTML = `<span style="color:${clr};font-weight:800;font-size:1.05rem;">${icon}</span><span style="font-size:0.875rem;color:#3A5563;">${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => {
    t.style.cssText +=
      "opacity:0;transform:translateX(16px);transition:all 0.3s;";
    setTimeout(() => t.remove(), 300);
  }, 3800);
}

/* ════════════════════════════════════════════════════════════════
   [E] PORTAL — LOGIN / REGISTER
════════════════════════════════════════════════════════════════ */
function initPortal() {
  const s = getSession();
  if (s) {
    window.location.href =
      s.role === "doctor" ? "doctor-dashboard.html" : "patient-dashboard.html";
    return;
  }

  window.switchPortalTab = function (tabId, btn) {
    document
      .querySelectorAll(".ptab-btn")
      .forEach((b) => b.classList.remove("active"));
    document
      .querySelectorAll(".ptab-panel")
      .forEach((t) => t.classList.remove("active"));
    if (btn) btn.classList.add("active");
    document.getElementById(tabId)?.classList.add("active");
  };

  window.handleLogin = async function () {
    const email = document.getElementById("loginEmail")?.value.trim();
    const pass = document.getElementById("loginPass")?.value.trim();
    if (!email || !pass) {
      showToast("Please enter your credentials.", "error");
      return;
    }

    const btn = document.getElementById("loginBtn");
    const orig = btn?.textContent;
    if (btn) {
      btn.textContent = "Please wait…";
      btn.disabled = true;
    }

    try {
      const data = await api(
        "POST",
        "/auth/login",
        { email, password: pass },
        false,
      );
      setToken(data.access_token);
      setCachedUser(data.user);
      showToast(`Welcome back, ${data.user.name.split(" ")[0]}!`);
      setTimeout(() => {
        window.location.href =
          data.user.role === "doctor"
            ? "doctor-dashboard.html"
            : "patient-dashboard.html";
      }, 600);
    } catch (e) {
      showToast(e.message || "Invalid email or password.", "error");
      if (btn) {
        btn.textContent = orig;
        btn.disabled = false;
      }
    }
  };

  window.handleRegister = async function () {
    const name = document.getElementById("regName")?.value.trim();
    const email = document.getElementById("regEmail")?.value.trim();
    const phone = document.getElementById("regPhone")?.value.trim();
    const pass = document.getElementById("regPass")?.value.trim();
    const code = document.getElementById("regCode")?.value.trim();
    if (!name || !email || !pass) {
      showToast("Please fill all required fields.", "error");
      return;
    }

    const btn = document.getElementById("registerBtn");
    const orig = btn?.textContent;
    if (btn) {
      btn.textContent = "Please wait…";
      btn.disabled = true;
    }

    const body = { name, email, password: pass };
    if (phone) body.phone = phone;
    if (code) body.doctor_access_code = code;

    try {
      const data = await api("POST", "/auth/register", body, false);
      setToken(data.access_token);
      setCachedUser(data.user);
      showToast("Account created!");
      setTimeout(() => {
        window.location.href =
          data.user.role === "doctor"
            ? "doctor-dashboard.html"
            : "patient-dashboard.html";
      }, 700);
    } catch (e) {
      showToast(
        e.message || "Registration failed. Email may already exist.",
        "error",
      );
      if (btn) {
        btn.textContent = orig;
        btn.disabled = false;
      }
    }
  };
}

/* Forgot password — kept as a local lookup notice; no backend reset flow exists yet */
window.openForgotModal = function () {
  const m = document.getElementById("forgotModal");
  if (m) {
    m.classList.add("open");
    document.body.style.overflow = "hidden";
  }
};
window.closeForgotModal = function () {
  const m = document.getElementById("forgotModal");
  if (m) {
    m.classList.remove("open");
    document.body.style.overflow = "";
  }
};
window.handleForgotPassword = function () {
  const result = document.getElementById("forgotResult");
  if (!result) return;
  result.style.display = "block";
  result.style.background = "#DCF0FA";
  result.style.border = "1px solid #9DD0F0";
  result.style.borderRadius = "10px";
  result.style.padding = "13px 15px";
  result.style.color = "#1A6496";
  result.innerHTML = `<div style="font-size:0.875rem;">Password reset isn't wired up to a real email/SMS flow yet — please contact support directly for now.</div>`;
};

/* ════════════════════════════════════════════════════════════════
   [F] DOCTOR PICKER — patient selects their doctor
   🆕 NEEDS BACKEND:
     - GET /doctors                      → list of {id,name,specialty,hospital,patient_count}
     - PATCH /auth/me  body:{doctor_id}  → extend existing endpoint to accept doctor_id
     - GET /auth/me must return doctor_id (and doctor_name/specialty/hospital if you want
       to avoid a second lookup)
════════════════════════════════════════════════════════════════ */
async function renderDoctorPicker() {
  const container = document.getElementById("doctorPickerSection");
  if (!container) return;
  container.innerHTML =
    '<p style="font-size:0.82rem;color:#7A9CA8;text-align:center;padding:16px;">Loading doctors…</p>';

  try {
    const [me, doctors] = await Promise.all([
      refreshMe(),
      api("GET", "/doctors"), // 🆕 NEEDS BACKEND
    ]);

    const myDoc = me.doctor_id
      ? doctors.find((d) => d.id === me.doctor_id)
      : null;

    let assignedHTML = "";
    if (myDoc) {
      const initials = myDoc.name
        .split(" ")
        .filter((n) => n !== "Dr.")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();
      assignedHTML = `
        <div style="background:#EDF5F2;border:1px solid #9DD1C2;border-radius:12px;padding:14px 16px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#1B5271,#3A8DC4);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.85rem;color:#FFFFFF;flex-shrink:0;">${initials}</div>
          <div style="flex:1;">
            <div style="font-weight:700;color:#1B5271;font-size:0.92rem;">${myDoc.name}</div>
            <div style="font-size:0.76rem;color:#5DAC96;font-weight:600;margin-top:1px;">✓ Your assigned doctor</div>
            <div style="font-size:0.74rem;color:#7A9CA8;margin-top:2px;">${myDoc.specialty || "General Medicine"} · ${myDoc.hospital || "HAMAT Hospital"}</div>
          </div>
          <button onclick="selectDoctor(null)"
            style="background:#FAE8E8;border:1px solid #F0AAAA;border-radius:8px;padding:5px 12px;font-size:0.72rem;font-weight:700;color:#D94F4F;cursor:pointer;font-family:'Outfit',sans-serif;white-space:nowrap;">
            Change Doctor
          </button>
        </div>`;
    } else {
      assignedHTML = `
        <div style="background:#FBF0DC;border:1px solid #F0CC88;border-radius:10px;padding:11px 14px;margin-bottom:14px;display:flex;gap:9px;align-items:flex-start;">
          <span style="font-size:1rem;flex-shrink:0;">⚠️</span>
          <p style="font-size:0.83rem;color:#A0620A;margin:0;line-height:1.6;">You haven't selected a doctor yet. Your medication logs won't be visible to any doctor until you do.</p>
        </div>`;
    }

    const doctorCards = doctors
      .map((doc) => {
        const isSelected = me.doctor_id === doc.id;
        const initials = doc.name
          .split(" ")
          .filter((n) => n !== "Dr.")
          .map((n) => n[0])
          .join("")
          .slice(0, 2)
          .toUpperCase();
        return `
        <div style="background:#FFFFFF;border:1.5px solid ${isSelected ? "#5DAC96" : "#D1E4DE"};border-radius:13px;padding:14px 16px;
                    display:flex;align-items:center;gap:12px;cursor:pointer;transition:all 0.2s;margin-bottom:8px;
                    ${isSelected ? "box-shadow:0 4px 18px rgba(93,172,150,0.18);" : ""}"
             onclick="selectDoctor('${doc.id}')">
          <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#1B5271,#3A8DC4);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.85rem;color:#FFFFFF;flex-shrink:0;">${initials}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:700;color:#1B5271;font-size:0.9rem;">${doc.name}</div>
            <div style="font-size:0.74rem;color:#7A9CA8;margin-top:2px;">${doc.specialty || "General Medicine"} · ${doc.hospital || "HAMAT Hospital"}</div>
            <div style="font-size:0.71rem;color:#7A9CA8;margin-top:1px;">${doc.patient_count ?? 0} patient(s) assigned</div>
          </div>
          <div style="flex-shrink:0;">
            ${
              isSelected
                ? '<span style="font-size:0.68rem;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#2E7A65;background:#D5F3EB;padding:4px 11px;border-radius:100px;">✓ Selected</span>'
                : '<span style="font-size:0.68rem;font-weight:600;color:#7A9CA8;">Select →</span>'
            }
          </div>
        </div>`;
      })
      .join("");

    container.innerHTML =
      assignedHTML +
      `
      <div style="font-size:0.72rem;font-weight:700;color:#7A9CA8;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:12px;">
        Available Doctors at HAMAT Hospital
      </div>
      ${doctorCards || '<p style="font-size:0.82rem;color:#7A9CA8;">No doctors registered yet.</p>'}`;
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load doctors: ${e.message}</p>`;
  }
}

window.selectDoctor = async function (doctorId) {
  try {
    await api("PATCH", "/auth/me", { doctor_id: doctorId }); // 🆕 NEEDS BACKEND (extend schema)
    await refreshMe();
    showToast(
      doctorId
        ? "✓ Doctor updated — they can now see your logs."
        : "Doctor removed.",
    );
    await renderDoctorPicker();
    await renderCurrentDoctorSummary();
  } catch (e) {
    showToast(e.message || "Could not update doctor.", "error");
  }
};

async function renderCurrentDoctorSummary() {
  const card = document.getElementById("currentDoctorCard");
  if (!card) return;
  try {
    const [me, doctors] = await Promise.all([
      refreshMe(),
      api("GET", "/doctors"),
    ]); // 🆕 NEEDS BACKEND
    const doc = me.doctor_id
      ? doctors.find((d) => d.id === me.doctor_id)
      : null;
    if (!doc) {
      card.innerHTML =
        '<p style="font-size:0.82rem;color:#7A9CA8;text-align:center;padding:12px;">No doctor selected yet. Use the picker on the left.</p>';
      return;
    }
    const initials = doc.name
      .split(" ")
      .filter((n) => n !== "Dr.")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    card.innerHTML = `
      <div style="display:flex;align-items:center;gap:13px;padding:12px 0;">
        <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#1B5271,#3A8DC4);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.9rem;color:#FFFFFF;flex-shrink:0;">${initials}</div>
        <div>
          <div style="font-weight:700;color:#1B5271;font-size:0.95rem;">${doc.name}</div>
          <div style="font-size:0.75rem;color:#5DAC96;font-weight:600;margin-top:1px;">✓ Your assigned doctor</div>
          <div style="font-size:0.73rem;color:#7A9CA8;margin-top:2px;">${doc.specialty || "General Medicine"} · ${doc.hospital || "HAMAT Hospital"}</div>
        </div>
      </div>`;
  } catch (e) {
    card.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;">${e.message}</p>`;
  }
}

/* ════════════════════════════════════════════════════════════════
   [G] PATIENT DASHBOARD INIT
════════════════════════════════════════════════════════════════ */
async function initPatientDashboard() {
  requireRole("patient");
  const s = getSession();
  const nameEl = document.getElementById("patientName");
  if (nameEl) nameEl.textContent = s.name;
  ["medDate", "medStartDate"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.valueAsDate = new Date();
  });
  const endEl = document.getElementById("medEndDate");
  if (endEl) {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    endEl.valueAsDate = d;
  }

  await Promise.all([
    renderPatientKPIs(),
    renderPatientLogs(),
    renderCareFeed(),
    renderPharmacyMessages(),
    renderCaregivers(),
    renderMedRequests(),
    renderSchedules(),
  ]);
  setTimeout(renderPatientChart, 200);

  setInterval(() => {
    renderCareFeed();
    renderPharmacyMessages();
    updateUnreadBadge();
  }, 5000);

  const hrsEl = document.getElementById("medIntervalHrs");
  if (hrsEl) hrsEl.addEventListener("input", updateIntervalPreview);

  const form = document.getElementById("medForm");
  if (form) form.addEventListener("submit", handleMedFormSubmit);

  window.setStatusUI = function (val) {
    const takenCb = document.getElementById("medTaken");
    if (takenCb) {
      takenCb.checked = val === "taken";
      if (val) takenCb.dataset.selected = "yes";
      else delete takenCb.dataset.selected;
    }
    ["taken", "missed"].forEach((v) => {
      const lbl = document.getElementById("lbl-" + v);
      if (!lbl) return;
      const active = val === v;
      lbl.style.borderColor = active
        ? v === "taken"
          ? "#5DAC96"
          : "#D94F4F"
        : "#D1E4DE";
      lbl.style.background = active
        ? v === "taken"
          ? "#EDF5F2"
          : "#FAE8E8"
        : "#FFFFFF";
    });
  };

  window.markNoteRead = async function (noteId) {
    try {
      await api("PATCH", `/notes/${noteId}/read`); // ✅ real route, no body needed
      renderCareFeed();
      updateUnreadBadge();
    } catch (e) {
      /* non-critical — fail silently, note stays unread visually */
    }
  };

  updateUnreadBadge();
  updateIntervalPreview();
}

/* ════════════════════════════════════════════════════════════════
   [H] MEDICATION LOGGING (+ optional schedule creation)
   POST /logs                → existing, unchanged
   POST /schedules            → 🆕 NEEDS BACKEND (new table + router)
════════════════════════════════════════════════════════════════ */
async function handleMedFormSubmit(e) {
  e.preventDefault();
  const med = document.getElementById("medName").value.trim();
  const dosage = document.getElementById("medDosage")?.value.trim() || "";
  const date = document.getElementById("medDate").value;
  const takenCb = document.getElementById("medTaken");
  const notes = document.getElementById("medNotes").value.trim();
  const time = document.getElementById("medTime").value || null;

  if (!med || !date) {
    showToast("Please fill required fields.", "error");
    return;
  }
  if (!takenCb.dataset.selected) {
    showToast("Please select Taken or Missed.", "error");
    return;
  }
  const taken = takenCb.checked;

  const startDate = document.getElementById("medStartDate")?.value || date;
  const endDate = document.getElementById("medEndDate")?.value || "";
  const intervalHrs =
    parseInt(document.getElementById("medIntervalHrs")?.value) || 0;
  const firstTime = document.getElementById("medFirstTime")?.value || "08:00";

  try {
    // 1) Always log the dose event
    await api("POST", "/logs", {
      medicine_name: med,
      log_date: date,
      taken,
      time_taken: time,
      notes,
    });

    // 2) Optionally create a repeating schedule
    if (startDate && endDate && intervalHrs > 0) {
      try {
        await api("POST", "/schedules", {
          // 🆕 NEEDS BACKEND
          medicine_name: med,
          dosage,
          start_date: startDate,
          end_date: endDate,
          interval_hours: intervalHrs,
          first_dose_time: firstTime,
          notes,
        });
        showToast(
          `Schedule: ${med} every ${intervalHrs}hrs (${dosesPerDay(intervalHrs)}×/day) — SMS reminders enabled`,
          "info",
        );
      } catch (schedErr) {
        showToast(
          "Log saved, but schedule creation failed: " + schedErr.message,
          "error",
        );
      }
    }

    await Promise.all([
      renderPatientLogs(),
      renderPatientKPIs(),
      renderSchedules(),
    ]);
    setTimeout(renderPatientChart, 100);

    e.target.reset();
    document.getElementById("medDate").valueAsDate = new Date();
    document.getElementById("medStartDate").valueAsDate = new Date();
    const ed2 = document.getElementById("medEndDate");
    if (ed2) {
      const d = new Date();
      d.setDate(d.getDate() + 30);
      ed2.valueAsDate = d;
    }
    setStatusUI(null);
    updateIntervalPreview();

    if (!taken && notes.toLowerCase().includes("ran out"))
      await flagMedicineOut(med, dosage, notes);
    showToast("Medication logged!");
  } catch (err) {
    showToast(err.message || "Failed to save log.", "error");
  }
}

function updateIntervalPreview() {
  const hrsEl = document.getElementById("medIntervalHrs");
  const prev = document.getElementById("intervalPreview");
  if (!prev) return;
  const hrs = parseInt(hrsEl?.value) || 0;
  if (!hrs || hrs < 1) {
    prev.style.display = "none";
    return;
  }
  const dpd = dosesPerDay(hrs);
  prev.style.display = "block";
  prev.innerHTML = `<span style="color:#9DD1C2;font-weight:700;">1×${dpd}</span> — take 1 dose every <strong style="color:#FFFFFF;">${hrs} hours</strong> (${dpd} time${dpd !== 1 ? "s" : ""}/day) &nbsp;·&nbsp; SMS reminder fires at each dose time`;
}

/* ════════════════════════════════════════════════════════════════
   [I] SCHEDULES TAB
   GET /schedules              → 🆕 NEEDS BACKEND
   PATCH /schedules/{id}       → 🆕 NEEDS BACKEND (toggle active)
   Test SMS reuses the REAL endpoint: POST /reminders/send-now
════════════════════════════════════════════════════════════════ */
async function renderSchedules() {
  const container = document.getElementById("schedulesList");
  if (!container) return;
  try {
    const sch = await api("GET", "/schedules"); // 🆕 NEEDS BACKEND
    if (!sch || !sch.length) {
      container.innerHTML = `<div style="text-align:center;padding:24px 14px;"><div style="font-size:2rem;margin-bottom:8px;">📅</div><p style="font-size:0.82rem;color:#7A9CA8;">No schedules yet. Fill in Start Date, End Date and Interval Hrs when logging a medication.</p></div>`;
      return;
    }
    const today = new Date().toISOString().split("T")[0];
    container.innerHTML = sch
      .slice()
      .reverse()
      .map((sc) => {
        const dpd = dosesPerDay(sc.interval_hours);
        const active =
          sc.active && today >= sc.start_date && today <= sc.end_date;
        const doses = dosesUpcomingLocal(sc, 3);
        const upcoming = doses
          .map((d) => {
            const hh = String(d.getHours()).padStart(2, "0");
            const mm = String(d.getMinutes()).padStart(2, "0");
            return `${d.toLocaleDateString("en-KE", { month: "short", day: "numeric" })} ${hh}:${mm}`;
          })
          .join(" · ");
        return `<div style="background:#FFFFFF;border:1px solid ${active ? "#9DD1C2" : "#D1E4DE"};border-left:3px solid ${active ? "#5DAC96" : "#7A9CA8"};border-radius:12px;padding:14px 16px;margin-bottom:10px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap;">
          <div style="flex:1;">
            <div style="font-weight:700;color:#1B5271;font-size:0.92rem;">${sc.medicine_name}${sc.dosage ? " · " + sc.dosage : ""}</div>
            <div style="font-size:0.78rem;color:#7A9CA8;margin-top:3px;">📅 ${fmtDate(sc.start_date)} → ${fmtDate(sc.end_date)} &nbsp;·&nbsp; Every <strong style="color:#1B5271;">${sc.interval_hours}hrs</strong> &nbsp;·&nbsp; <strong style="color:#5DAC96;">1×${dpd}</strong>/day</div>
            <div style="font-size:0.75rem;color:#7A9CA8;margin-top:3px;">⏰ First dose: <strong style="color:#1B5271;">${sc.first_dose_time}</strong> &nbsp;·&nbsp; Next 3: ${upcoming || "—"}</div>
          </div>
          <div style="display:flex;gap:6px;align-items:center;flex-shrink:0;">
            <span style="font-size:0.68rem;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;padding:3px 10px;border-radius:100px;${active ? "background:#D5F3EB;color:#1E8A65;" : "background:#EDF5F2;color:#7A9CA8;"}">${active ? "Active" : "Inactive"}</span>
            <button onclick="testScheduleSMS()" style="background:#EDF5F2;border:1px solid #D1E4DE;border-radius:7px;padding:4px 10px;font-size:0.72rem;font-weight:700;color:#5DAC96;cursor:pointer;font-family:'Outfit',sans-serif;white-space:nowrap;">📱 Test SMS</button>
            <button onclick="toggleSchedule('${sc.id}', ${!sc.active})" style="background:${active ? "#FAE8E8" : "#D5F3EB"};border:1px solid ${active ? "#F0AAAA" : "#A8E4D0"};border-radius:7px;padding:4px 10px;font-size:0.72rem;font-weight:700;color:${active ? "#D94F4F" : "#1E8A65"};cursor:pointer;font-family:'Outfit',sans-serif;white-space:nowrap;">${active ? "Pause" : "Resume"}</button>
          </div>
        </div>
      </div>`;
      })
      .join("");
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load schedules: ${e.message}</p>`;
  }
}

/* Test SMS now uses the REAL backend endpoint — sends to caregivers + self */
window.testScheduleSMS = async function () {
  await sendReminderNow();
};

window.toggleSchedule = async function (id, newActive) {
  try {
    await api("PATCH", `/schedules/${id}`, { active: newActive }); // 🆕 NEEDS BACKEND
    renderSchedules();
  } catch (e) {
    showToast(e.message || "Failed to update schedule.", "error");
  }
};

/* ════════════════════════════════════════════════════════════════
   [J] SMS LOG
   There is no persisted backend SMS log yet. This renders a
   session-only log built from the results of each /reminders/send-now
   call (see sendReminderNow below). Refreshing the page clears it.
   🆕 OPTIONAL BACKEND: a real sms_log table + GET /reminders/sms-log
   would make this persist across sessions/devices.
════════════════════════════════════════════════════════════════ */
function getSessionSMSLog() {
  try {
    return JSON.parse(sessionStorage.getItem("dt_sms_log_session")) || [];
  } catch {
    return [];
  }
}
function pushSessionSMSLog(entries) {
  const log = getSessionSMSLog();
  entries.forEach((name) =>
    log.push({ name, sentAt: new Date().toISOString() }),
  );
  sessionStorage.setItem("dt_sms_log_session", JSON.stringify(log));
}

function renderSMSLog() {
  const container = document.getElementById("smsLog");
  if (!container) return;
  const log = getSessionSMSLog().slice().reverse();
  if (!log.length) {
    container.innerHTML =
      '<p style="font-size:0.82rem;color:#7A9CA8;text-align:center;padding:16px;">No SMS sent this session yet. Click "Test SMS" on a schedule, or use the button in Caregivers tab.</p>';
    return;
  }
  container.innerHTML = log
    .map(
      (l) => `
    <div class="sms-entry">
      <span style="font-size:1.1rem;flex-shrink:0;">📱</span>
      <div style="flex:1;min-width:0;">
        <div style="font-size:0.82rem;color:#3A5563;">Sent to <strong>${l.name}</strong></div>
        <div style="font-size:0.70rem;color:#7A9CA8;margin-top:4px;">${new Date(l.sentAt).toLocaleString("en-KE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</div>
      </div>
    </div>`,
    )
    .join("");
}

/* Shared reminder sender — calls the REAL backend, used by both the
   Caregivers tab button and the Schedules "Test SMS" button. */
async function sendReminderNow() {
  try {
    const result = await api("POST", "/reminders/send-now"); // ✅ REAL, EXISTING ENDPOINT
    const sent = result.sent_to || [];
    const failed = result.failed || [];
    if (sent.length) {
      pushSessionSMSLog(sent);
      showToast(`📱 SMS sent to: ${sent.join(", ")}`, "success");
    }
    if (failed.length)
      showToast(`Failed to send to: ${failed.join(", ")}`, "error");
    if (!sent.length && !failed.length)
      showToast(result.detail || "No recipients found.", "info");
    renderSMSLog();
  } catch (e) {
    showToast(e.message || "Failed to send SMS.", "error");
  }
}
window.simulateSMSNow = sendReminderNow;

/* ════════════════════════════════════════════════════════════════
   [K] CAREGIVERS — real backend, already built earlier
════════════════════════════════════════════════════════════════ */
async function renderCaregivers() {
  const container = document.getElementById("caregiversList");
  if (!container) return;
  try {
    const cgs = await api("GET", "/caregivers");
    if (!cgs || !cgs.length) {
      container.innerHTML = `<div style="text-align:center;padding:28px;color:#7A9CA8;font-size:0.85rem;"><div style="font-size:2rem;margin-bottom:8px;">👨‍👩‍👧</div>No caregivers added yet.<br>Click "+ Add Person" to add one.</div>`;
      return;
    }
    const relIcon = {
      spouse: "💑",
      partner: "💑",
      parent: "👪",
      sibling: "👫",
      child: "👶",
      relative: "👨‍👩‍👧",
      caregiver: "🧑‍⚕️",
      friend: "🤝",
      me: "👤",
    };
    container.innerHTML = cgs
      .map(
        (c) => `
      <div style="background:#FFFFFF;border:1px solid #D1E4DE;border-radius:12px;padding:14px;margin-bottom:10px;display:flex;align-items:center;gap:12px;">
        <div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#5DAC96,#1B5271);display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">${relIcon[c.relationship] || "👤"}</div>
        <div style="flex:1;">
          <div style="font-weight:700;color:#1B5271;font-size:0.92rem;">${c.name}</div>
          <div style="font-size:0.75rem;color:#7A9CA8;margin-top:2px;">${c.phone} · ${relLabel(c.relationship)}</div>
          ${c.reminders_enabled ? '<div style="font-size:0.70rem;color:#5DAC96;margin-top:2px;">📱 Will receive SMS reminders</div>' : '<div style="font-size:0.70rem;color:#7A9CA8;margin-top:2px;">SMS reminders off</div>'}
        </div>
        <button onclick="removeCg(${c.id})" style="background:#FAE8E8;border:1px solid #F0AAAA;border-radius:8px;padding:5px 10px;font-size:0.75rem;color:#D94F4F;cursor:pointer;font-family:Outfit,sans-serif;font-weight:600;">Remove</button>
      </div>`,
      )
      .join("");
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load caregivers: ${e.message}</p>`;
  }
}

window.openCgModal = function () {
  const m = document.getElementById("cgModal");
  if (m) {
    m.classList.add("open");
    document.body.style.overflow = "hidden";
  }
};
window.closeCgModal = function () {
  const m = document.getElementById("cgModal");
  if (m) {
    m.classList.remove("open");
    document.body.style.overflow = "";
  }
};

window.onCgRelChange = function () {
  const rel = document.getElementById("cg-rel")?.value;
  const s = getSession();
  if (rel === "me") {
    const nameEl = document.getElementById("cg-name");
    const phoneEl = document.getElementById("cg-phone");
    if (nameEl && !nameEl.value) nameEl.value = s.name || "";
    if (phoneEl && !phoneEl.value) phoneEl.value = s.phone || "";
  }
};

window.submitCg = async function () {
  const name = document.getElementById("cg-name")?.value.trim();
  const phone = document.getElementById("cg-phone")?.value.trim();
  const rel = document.getElementById("cg-rel")?.value || "relative";
  const reminders = document.getElementById("cg-reminders")?.checked !== false;
  if (!name || !phone) {
    showToast("Please enter name and phone number.", "error");
    return;
  }
  try {
    await api("POST", "/caregivers", {
      name,
      phone,
      relationship: rel,
      reminders_enabled: reminders,
    });
    showToast(`${name} added as caregiver!`);
    document.getElementById("cg-name").value = "";
    document.getElementById("cg-phone").value = "";
    closeCgModal();
    await renderCaregivers();
  } catch (e) {
    showToast(e.message || "Failed to add caregiver.", "error");
  }
};

window.removeCg = async function (cgId) {
  try {
    await api("DELETE", `/caregivers/${cgId}`);
    showToast("Caregiver removed.");
    await renderCaregivers();
  } catch (e) {
    showToast(e.message || "Failed to remove caregiver.", "error");
  }
};

/* ════════════════════════════════════════════════════════════════
   [L] MEDICINE REQUESTS — real backend (POST/GET /requests)
════════════════════════════════════════════════════════════════ */
async function flagMedicineOut(medicine, dosage, notes) {
  try {
    await api("POST", "/requests", {
      medicine_name: medicine,
      dosage,
      message: notes || "Medicine out — requesting refill.",
    });
    showToast("Pharmacy notified that you need " + medicine, "info");
  } catch (e) {
    showToast(e.message || "Failed to notify pharmacy.", "error");
  }
}
window.openMedOutModal = function () {
  const m = document.getElementById("medOutModal");
  if (m) {
    m.classList.add("open");
    document.body.style.overflow = "hidden";
  }
};
window.closeMedOutModal = function () {
  const m = document.getElementById("medOutModal");
  if (m) {
    m.classList.remove("open");
    document.body.style.overflow = "";
  }
};
window.submitMedRequest = async function () {
  const med = document.getElementById("req-medicine")?.value.trim();
  const dosage = document.getElementById("req-dosage")?.value.trim() || "";
  const msg = document.getElementById("req-message")?.value.trim() || "";
  if (!med) {
    showToast("Please enter medicine name.", "error");
    return;
  }
  await flagMedicineOut(med, dosage, msg || "Requesting refill.");
  renderMedRequests();
  closeMedOutModal();
};
async function renderMedRequests() {
  const container = document.getElementById("medRequestsList");
  if (!container) return;
  try {
    const reqs = await api("GET", "/requests/mine");
    if (!reqs.length) {
      container.innerHTML =
        '<p style="font-size:0.82rem;color:#7A9CA8;text-align:center;padding:16px;">No active requests.</p>';
      return;
    }
    container.innerHTML = reqs
      .map((r) => {
        const sc =
          r.status === "pending"
            ? { clr: "#A0620A", bg: "#FBF0DC" }
            : r.status === "fulfilled"
              ? { clr: "#1E8A65", bg: "#D5F3EB" }
              : { clr: "#7A9CA8", bg: "#EDF5F2" };
        return `<div style="background:#FFFFFF;border:1px solid #D1E4DE;border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start;">
        <div style="width:36px;height:36px;border-radius:10px;background:${sc.bg};display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;">💊</div>
        <div style="flex:1;"><div style="font-weight:700;color:#1B5271;font-size:0.9rem;">${r.medicine_name}${r.dosage ? " · " + r.dosage : ""}</div><div style="font-size:0.78rem;color:#7A9CA8;margin-top:2px;">${r.message || ""}</div><div style="margin-top:8px;display:flex;align-items:center;gap:8px;"><span style="font-size:0.68rem;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:${sc.clr};background:${sc.bg};padding:3px 10px;border-radius:100px;">${r.status}</span><span style="font-size:0.7rem;color:#7A9CA8;">${timeAgo(r.created_at)}</span></div>${r.pharmacy_reply ? `<div style="margin-top:10px;background:#EDF5F2;border:1px solid #9DD1C2;border-left:3px solid #5DAC96;border-radius:8px;padding:10px 12px;font-size:0.82rem;color:#1B5271;"><strong>🏪 Pharmacy:</strong> ${r.pharmacy_reply}</div>` : ""}</div></div>`;
      })
      .join("");
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load requests: ${e.message}</p>`;
  }
}

/* ════════════════════════════════════════════════════════════════
   [M] PHARMACY FEED — real backend. Built from replied requests +
   dispensing history, since there's no separate "messages" table.
════════════════════════════════════════════════════════════════ */
async function renderPharmacyMessages() {
  const container = document.getElementById("pharmacyFeed");
  if (!container) return;
  try {
    const [reqs, dispensed] = await Promise.all([
      api("GET", "/requests/mine"),
      api("GET", "/dispense/mine"),
    ]);
    const replies = reqs
      .filter((r) => r.pharmacy_reply)
      .map((r) => ({
        kind: "reply",
        ts: r.updated_at,
        subject: r.medicine_name + " — Pharmacy Reply",
        message: r.pharmacy_reply,
        pharmacistName: r.pharmacist_name,
      }));
    const dispenses = dispensed.map((d) => ({
      kind: "dispense",
      ts: d.created_at,
      subject: d.medicine_name + " — Dispensed",
      message: `${d.quantity || 1}x ${d.medicine_name}${d.dosage ? " (" + d.dosage + ")" : ""} dispensed to you.`,
      pharmacistName: d.pharmacist_name,
    }));
    const feed = [...replies, ...dispenses].sort(
      (a, b) => new Date(b.ts) - new Date(a.ts),
    );
    if (!feed.length) {
      container.innerHTML =
        '<p style="font-size:0.82rem;color:#7A9CA8;text-align:center;padding:20px;">No pharmacy messages yet.</p>';
      return;
    }
    container.innerHTML = feed
      .map(
        (
          m,
        ) => `<div style="background:#FFFFFF;border:1px solid #D1E4DE;border-left:3px solid #5DAC96;border-radius:12px;padding:14px 16px;margin-bottom:10px;">
      <div style="display:flex;gap:10px;align-items:flex-start;"><span style="font-size:1.1rem;flex-shrink:0;">🏪</span><div style="flex:1;"><div style="font-size:0.70rem;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;color:#5DAC96;margin-bottom:5px;">Pharmacy · ${m.subject}</div><p style="font-size:0.84rem;color:#3A5563;margin:0;line-height:1.6;">${m.message}</p><div style="font-size:0.70rem;color:#7A9CA8;margin-top:6px;">— ${m.pharmacistName || "Pharmacist"} · ${timeAgo(m.ts)}</div></div></div>
    </div>`,
      )
      .join("");
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load pharmacy feed.</p>`;
  }
}

/* ════════════════════════════════════════════════════════════════
   [N] CARE FEED (doctor → patient notes) — real backend
════════════════════════════════════════════════════════════════ */
async function renderCareFeed() {
  const cnt = document.getElementById("careFeed");
  if (!cnt) return;
  try {
    const { notes } = await api("GET", "/notes/feed"); // ✅ backend returns {total, skip, limit, notes}
    if (!notes || !notes.length) {
      cnt.innerHTML = `<div style="text-align:center;padding:28px 14px;"><div style="font-size:2rem;margin-bottom:10px;">🩺</div><p style="font-size:0.82rem;color:#7A9CA8;">No messages yet.</p></div>`;
      return;
    }
    cnt.innerHTML = notes
      .map((n) => {
        const st = noteTypeStyle(n.note_type); // ✅ field is note_type, not type
        return `<div style="background:${n.is_read ? "#FFFFFF" : st.bg};border:1px solid ${n.is_read ? "#D1E4DE" : st.border};border-radius:14px;padding:14px;margin-bottom:10px;cursor:pointer;position:relative;" onclick="markNoteRead(${n.id})">
        ${!n.is_read ? `<div style="position:absolute;top:10px;right:12px;width:8px;height:8px;border-radius:50%;background:${st.accentBg};"></div>` : ""}
        <div style="display:flex;gap:10px;align-items:flex-start;"><div style="width:34px;height:34px;border-radius:9px;background:${st.accentBg};display:flex;align-items:center;justify-content:center;font-size:0.95rem;flex-shrink:0;">${st.icon}</div><div style="flex:1;min-width:0;"><div style="display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;margin-bottom:5px;"><span style="font-size:0.68rem;font-weight:800;letter-spacing:0.07em;text-transform:uppercase;color:${st.labelColor};">${st.label}</span><span style="font-size:0.68rem;color:#7A9CA8;">${timeAgo(n.created_at)}</span></div><p style="font-size:0.84rem;color:#3A5563;margin:0;line-height:1.6;">${n.message}</p><div style="font-size:0.70rem;color:#7A9CA8;margin-top:7px;font-weight:500;">— ${n.doctor_name || "Doctor"}</div></div></div>
      </div>`;
      })
      .join("");
  } catch (e) {
    cnt.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load feed.</p>`;
  }
}

async function renderFullFeed() {
  await renderCareFeed();
  const full = document.getElementById("careFeedFull");
  const mini = document.getElementById("careFeed");
  if (full && mini) full.innerHTML = mini.innerHTML;
}

async function updateUnreadBadge() {
  const s = getSession();
  if (!s) return;
  try {
    const data = await api("GET", "/notes/unread-count");
    const total = data.unread ?? 0; // ✅ backend returns {"unread": count}
    ["unreadBadge", "unreadBadge2"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = total;
      el.style.display = total > 0 ? "inline-flex" : "none";
    });
  } catch {
    /* non-critical */
  }
}

/* ════════════════════════════════════════════════════════════════
   [O] PATIENT LOGS + KPIs + CHART — real backend
════════════════════════════════════════════════════════════════ */
async function renderPatientKPIs() {
  try {
    const { logs, stats } = await api("GET", "/logs"); // ✅ destructure
    const rate = stats?.rate ?? adherenceRate(logs);
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    set("kpi-total", stats?.total ?? logs.length);
    set("kpi-taken", stats?.taken ?? logs.filter((l) => l.taken).length);
    set("kpi-missed", stats?.missed ?? logs.filter((l) => !l.taken).length);
    set("kpi-rate", rate + "%");
    const bar = document.getElementById("kpi-bar");
    if (bar) {
      bar.style.width = rate + "%";
      bar.className =
        "adherence-fill" +
        (rate >= 80 ? "" : rate >= 50 ? " warning" : " danger");
    }

    const sEl = document.getElementById("sidebar-rate");
    const sBar = document.getElementById("sidebar-bar");
    if (sEl) sEl.textContent = logs.length ? rate + "%" : "—";
    if (sBar) {
      sBar.style.width = (logs.length ? rate : 0) + "%";
      sBar.className =
        "adherence-fill" +
        (rate >= 80 ? "" : rate >= 50 ? " warning" : " danger");
    }
  } catch (e) {
    /* non-critical */
  }
}

async function renderPatientLogs() {
  const cnt = document.getElementById("patientLogs");
  if (!cnt) return;
  try {
    const { logs } = await api("GET", "/logs"); // ✅ destructure
    if (!logs.length) {
      cnt.innerHTML = `<div style="text-align:center;padding:56px 20px;background:#FFFFFF;border:1px solid #D1E4DE;border-radius:16px;"><div style="font-size:3rem;margin-bottom:14px;">💊</div><div style="font-weight:700;color:#1B5271;margin-bottom:6px;">No medications logged yet</div><p style="font-size:0.85rem;color:#7A9CA8;">Use the form to log your first dose.</p></div>`;
      return;
    }
    cnt.innerHTML = logs
      .slice()
      .reverse()
      .map((log) => {
        const notes = log.care_notes || [];
        return `<div style="background:#FFFFFF;border:1px solid #D1E4DE;border-radius:16px;overflow:hidden;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:14px;padding:18px 20px;flex-wrap:wrap;">
          <div style="width:46px;height:46px;border-radius:12px;background:${log.taken ? "#D5F3EB" : "#FAE0E0"};border:1px solid ${log.taken ? "#A8E4D0" : "#F0AAAA"};display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex-shrink:0;">${log.taken ? "✅" : "❌"}</div>
          <div style="flex:1;min-width:120px;"><div style="font-weight:700;font-size:0.95rem;color:#1B5271;">${log.medicine_name}</div><div style="font-size:0.76rem;color:#7A9CA8;margin-top:3px;">📅 ${fmtDate(log.log_date)}${log.time_taken ? " · ⏰ " + log.time_taken : ""}</div></div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            ${log.taken ? '<span class="badge badge-green">✓ Taken</span>' : '<span class="badge badge-red">✗ Missed</span>'}
            ${!log.taken ? `<button onclick="openMedOutModal()" style="background:#FBF0DC;border:1px solid #F0CC88;border-radius:7px;padding:4px 10px;font-size:0.72rem;font-weight:700;color:#A0620A;cursor:pointer;font-family:'Outfit',sans-serif;">💊 Need refill?</button>` : ""}
          </div>
        </div>
        ${log.notes ? `<div style="padding:0 20px 14px;display:flex;gap:8px;"><span style="color:#7A9CA8;">📝</span><p style="font-size:0.85rem;color:#3A5563;margin:0;line-height:1.6;">${log.notes}</p></div>` : ""}
        ${notes
          .map((n) => {
            const st = noteTypeStyle(n.note_type);
            return `<div style="margin:0 16px 14px;background:${st.bg};border:1px solid ${st.border};border-left:3px solid ${st.accentBg};border-radius:10px;padding:12px 14px;display:flex;gap:10px;"><span style="font-size:1.1rem;flex-shrink:0;">${st.icon}</span><div><div style="font-size:0.65rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:${st.labelColor};margin-bottom:4px;">Dr. Note · ${st.label}</div><p style="font-size:0.85rem;color:#3A5563;margin:0;line-height:1.6;">${n.message}</p><div style="font-size:0.70rem;color:#7A9CA8;margin-top:6px;">${fmtTime(n.created_at)} · ${n.doctor_name}</div></div></div>`;
          })
          .join("")}
      </div>`;
      })
      .join("");
  } catch (e) {
    cnt.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load logs: ${e.message}</p>`;
  }
}

async function renderPatientChart() {
  const canvas = document.getElementById("patientChart");
  if (!canvas || !window.Chart) return;
  const ex = Chart.getChart(canvas);
  if (ex) ex.destroy();
  try {
    const { stats } = await api("GET", "/logs"); // ✅ use backend's own trend_7d instead of recomputing
    const trend = stats?.trend_7d || [];
    const labels = trend.map((t) =>
      new Date(t.date + "T00:00:00").toLocaleDateString("en-KE", {
        day: "numeric",
        month: "short",
      }),
    );
    const taken = trend.map((t) => t.taken);
    const missed = trend.map((t) => t.missed);
    new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Taken",
            data: taken,
            backgroundColor: "rgba(93,172,150,0.75)",
            borderColor: "#5DAC96",
            borderWidth: 1,
            borderRadius: 6,
          },
          {
            label: "Missed",
            data: missed,
            backgroundColor: "rgba(217,79,79,0.45)",
            borderColor: "#D94F4F",
            borderWidth: 1,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#7A9CA8",
              font: { family: "Outfit", size: 11 },
              boxWidth: 12,
            },
          },
          tooltip: {
            backgroundColor: "#1B5271",
            titleColor: "#FFFFFF",
            bodyColor: "#9DD1C2",
            padding: 12,
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(209,228,222,0.5)" },
            ticks: { color: "#7A9CA8", font: { family: "Outfit", size: 11 } },
          },
          y: {
            beginAtZero: true,
            grid: { color: "rgba(209,228,222,0.5)" },
            ticks: {
              color: "#7A9CA8",
              stepSize: 1,
              font: { family: "Outfit", size: 11 },
            },
          },
        },
      },
    });
  } catch (e) {
    /* non-critical */
  }
}

/* ════════════════════════════════════════════════════════════════
   [P] DOCTOR DASHBOARD
   GET /patients — existing endpoint. ⚠️ Once doctor_id assignment
   ships, this endpoint MUST filter server-side to the logged-in
   doctor's own patients only (see backend notes).
════════════════════════════════════════════════════════════════ */
async function initDoctorDashboard() {
  requireRole("doctor");
  const s = getSession();
  const nEl = document.getElementById("doctorName");
  if (nEl) nEl.textContent = s.name;
  populateDoctorBanner();
  await renderDoctorOverview();
  await renderPatientList("all");
  setTimeout(() => {
    renderTrendChart();
    renderDonutChart();
    updateSidebarAtRisk();
  }, 200);

  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".filter-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderPatientList(btn.dataset.filter || "all");
    });
  });

  setInterval(() => {
    renderDoctorOverview();
    updateSidebarAtRisk();
    updateDrReqBadge();
    renderDrOverviewReqs();
  }, 8000);
  updateDrReqBadge();
  renderDrOverviewReqs();
}

async function populateDoctorBanner() {
  try {
    const me = await refreshMe();
    const initials = me.name
      .split(" ")
      .filter((n) => n !== "Dr.")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    const avatarEl = document.getElementById("drAvatar");
    if (avatarEl) avatarEl.textContent = initials;
    const metaEl = document.getElementById("doctorMeta");
    if (metaEl)
      metaEl.textContent = `${me.specialty || "General Medicine"} · ${me.hospital || "HAMAT Hospital"} · ${me.email}`;
  } catch {
    /* non-critical */
  }
}

async function fetchMyPatients() {
  const patients = await api("GET", "/patients?filter=all&limit=100");
  return Array.isArray(patients) ? patients : patients?.items || [];
}

async function renderDoctorOverview() {
  try {
    const overview = await api("GET", "/patients/overview");
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    set("dr-patients", overview.total_patients ?? "—");
    set("dr-rate", (overview.avg_adherence ?? 0) + "%");
    set("dr-atrisk", overview.at_risk_count ?? "—");
    set("dr-logs", overview.total_logs ?? "—");
    set("dr-unassigned", overview.unassigned_count ?? 0);
    const notice = document.getElementById("unassignedNotice");
    if (notice)
      notice.style.display =
        (overview.unassigned_count ?? 0) > 0 ? "flex" : "none";
  } catch (e) {
    /* non-critical */
  }
}

async function updateSidebarAtRisk() {
  try {
    const patients = await fetchMyPatients();
    const n = patients.filter(
      (p) => (p.adherence_rate ?? p.rate ?? 0) < 60,
    ).length;
    const el = document.getElementById("sidebar-atrisk");
    if (el) el.textContent = n;
  } catch {
    /* non-critical */
  }
}

async function renderPatientList(filter, customContainerId) {
  const container = document.getElementById(
    customContainerId || "doctorPatientList",
  );
  if (!container) return;
  container.innerHTML =
    '<p style="text-align:center;padding:30px;color:#7A9CA8;font-size:0.85rem;">Loading…</p>';
  try {
    let patients = await fetchMyPatients();
    patients = patients.map((p) => ({
      ...p,
      rate: p.adherence_rate ?? p.rate ?? 0,
    }));
    if (filter === "atrisk") patients = patients.filter((p) => p.rate < 60);
    else if (filter === "good") patients = patients.filter((p) => p.rate >= 80);
    patients.sort((a, b) => a.rate - b.rate);

    if (!patients.length) {
      container.innerHTML = `<div style="padding:40px;text-align:center;background:#FFFFFF;border:1px solid #D1E4DE;border-radius:16px;">
        <div style="font-size:2.5rem;margin-bottom:14px;">${filter === "atrisk" ? "🎉" : "👥"}</div>
        <div style="font-weight:700;color:#1B5271;margin-bottom:6px;">${filter === "atrisk" ? "No at-risk patients" : "No patients assigned yet"}</div>
        <p style="font-size:0.875rem;color:#7A9CA8;">${filter === "atrisk" ? "All your patients are above 60% adherence." : "Patients will appear here once they select you as their doctor from their dashboard."}</p>
      </div>`;
      return;
    }

    container.innerHTML = patients
      .map((p) => {
        const name = p.name || p.patient_name || "Patient";
        const initials = name
          .split(" ")
          .map((n) => n[0])
          .join("")
          .slice(0, 2)
          .toUpperCase();
        const avatarBg =
          p.rate >= 80
            ? "linear-gradient(135deg,#5DAC96,#9DD1C2)"
            : p.rate >= 50
              ? "linear-gradient(135deg,#D98A2A,#F0C070)"
              : "linear-gradient(135deg,#D94F4F,#F09090)";
        return `<div class="patient-card mb-3" style="margin-bottom:14px;">
        <div class="patient-card-header" onclick="toggleDetail('${p.id}')">
          <div class="patient-avatar" style="background:${avatarBg};width:48px;height:48px;font-size:1rem;flex-shrink:0;">${initials}</div>
          <div style="flex:1;min-width:120px;">
            <div style="font-weight:700;font-size:0.95rem;color:#1B5271;">${name}</div>
            <div style="font-size:0.75rem;color:#7A9CA8;margin-top:2px;">${p.email || p.phone || "—"} · ${p.total_logs ?? 0} logs</div>
          </div>
          <div style="min-width:90px;">${badgeAdherence(p.rate)}<div class="adherence-bar" style="margin-top:6px;width:90px;"><div class="adherence-fill${p.rate >= 80 ? "" : p.rate >= 50 ? " warning" : " danger"}" style="width:${p.rate}%;"></div></div></div>
          <div>${riskBadge(p.rate)}</div>
          <div style="color:#7A9CA8;font-size:0.75rem;margin-left:auto;user-select:none;" id="arr-${p.id}">▼ expand</div>
        </div>
        <div class="patient-card-detail" id="det-${p.id}" data-loaded="false">
          <p style="text-align:center;padding:20px;color:#7A9CA8;font-size:0.85rem;">Click to load logs…</p>
        </div>
      </div>`;
      })
      .join("");
  } catch (e) {
    container.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;padding:16px;">Failed to load patients: ${e.message}</p>`;
  }
}

window.toggleDetail = async function (pid) {
  const el = document.getElementById("det-" + pid);
  const arr = document.getElementById("arr-" + pid);
  if (!el) return;
  const open = el.style.display === "block";
  el.style.display = open ? "none" : "block";
  if (arr) arr.textContent = open ? "▼ expand" : "▲ collapse";
  if (!open && el.dataset.loaded !== "true") {
    try {
      const logs = await api("GET", `/patients/${pid}/logs?limit=50`);
      el.innerHTML = renderPatientDetailTable(pid, logs);
      el.dataset.loaded = "true";
    } catch (e) {
      el.innerHTML = `<p style="color:#D94F4F;font-size:0.85rem;">Failed to load logs: ${e.message}</p>`;
    }
  }
};

function renderPatientDetailTable(pid, logs) {
  const rows = logs
    .slice()
    .reverse()
    .map((log) => {
      const en = (log.care_notes || [])[0];
      return `<tr>
      <td style="white-space:nowrap;">${fmtDate(log.log_date)}</td>
      <td style="color:#1B5271;font-weight:600;">${log.medicine_name}</td>
      <td>${log.taken ? '<span class="badge badge-green">✓ Taken</span>' : '<span class="badge badge-red">✗ Missed</span>'}</td>
      <td style="color:#7A9CA8;">${log.time_taken || "—"}</td>
      <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#3A5563;">${log.notes || "—"}</td>
      <td>
        <select id="ntype-${log.id}" onclick="event.stopPropagation()" style="background:#FFFFFF;border:1px solid #D1E4DE;border-radius:7px;color:#1B5271;font-size:0.75rem;padding:5px 8px;font-family:'Outfit',sans-serif;cursor:pointer;margin-bottom:4px;width:100%;">
          <option value="advice"   ${en?.note_type === "advice" ? "selected" : ""}>💊 Advice</option>
          <option value="reminder" ${en?.note_type === "reminder" ? "selected" : ""}>🔔 Reminder</option>
          <option value="praise"   ${en?.note_type === "praise" ? "selected" : ""}>🌟 Praise</option>
          <option value="urgent"   ${en?.note_type === "urgent" ? "selected" : ""}>⚠️ Urgent</option>
        </select>
        <input type="text" placeholder="Write note to patient…" value="${en?.message || ""}" id="note-${log.id}" onclick="event.stopPropagation()" style="background:#FFFFFF;border:1px solid #D1E4DE;border-radius:7px;color:#0E1C28;font-size:0.78rem;padding:5px 10px;width:100%;font-family:'Outfit',sans-serif;">
      </td>
      <td><button class="btn-secondary" onclick="saveNote('${pid}',${log.id},event)" style="font-size:0.75rem;padding:5px 12px;white-space:nowrap;">Send →</button></td>
    </tr>`;
    })
    .join("");
  return `<div style="font-weight:700;font-size:0.875rem;color:#1B5271;margin-bottom:14px;">📋 Medication Log — send a care note via the last column</div>
    <div style="overflow-x:auto;"><table class="dt-table" style="min-width:700px;"><thead><tr><th>Date</th><th>Medication</th><th>Status</th><th>Time</th><th>Patient Notes</th><th>Your Note</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

window.saveNote = async function (patientId, logId, e) {
  e.stopPropagation();
  const input = document.getElementById("note-" + logId);
  const typeEl = document.getElementById("ntype-" + logId);
  const message = input?.value.trim();
  const type = typeEl?.value || "advice";
  if (!message) {
    showToast("Please write a note first.", "error");
    return;
  }
  try {
    await api("POST", "/notes", {
      patient_id: patientId,
      log_id: logId,
      message,
      note_type: type,
    });
    showToast(
      "Note sent to patient!" + (type === "urgent" ? " (SMS sent)" : ""),
    );
    const detailEl = document.getElementById("det-" + patientId);
    if (detailEl) detailEl.dataset.loaded = "false";
    toggleDetail(patientId);
    toggleDetail(patientId); // force reload
  } catch (err) {
    showToast(err.message || "Failed to send note.", "error");
  }
};

async function renderTrendChart() {
  const canvas = document.getElementById("trendChart");
  if (!canvas || !window.Chart) return;
  const ex = Chart.getChart(canvas);
  if (ex) ex.destroy();
  try {
    const overview = await api("GET", "/patients/overview");
    const trend = overview.trend_7d || [];
    const labels = trend.map((t) =>
      new Date(t.date + "T00:00:00").toLocaleDateString("en-KE", {
        day: "numeric",
        month: "short",
      }),
    );
    const rates = trend.map((t) => t.rate);
    new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Adherence %",
            data: rates,
            borderColor: "#5DAC96",
            backgroundColor: "rgba(93,172,150,0.10)",
            borderWidth: 2.5,
            pointBackgroundColor: "#5DAC96",
            pointBorderColor: "#FFFFFF",
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
            tension: 0.4,
            fill: true,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1B5271",
            titleColor: "#FFFFFF",
            bodyColor: "#9DD1C2",
            padding: 12,
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(209,228,222,0.5)" },
            ticks: { color: "#7A9CA8", font: { family: "Outfit", size: 11 } },
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: "rgba(209,228,222,0.5)" },
            ticks: {
              color: "#7A9CA8",
              font: { family: "Outfit", size: 11 },
              callback: (v) => v + "%",
            },
          },
        },
      },
    });
  } catch (e) {
    /* non-critical — overview may not return trend_7d yet */
  }
}

async function renderDonutChart() {
  const canvas = document.getElementById("donutChart");
  if (!canvas || !window.Chart) return;
  const ex = Chart.getChart(canvas);
  if (ex) ex.destroy();
  try {
    const patients = (await fetchMyPatients()).map((p) => ({
      ...p,
      rate: p.adherence_rate ?? p.rate ?? 0,
    }));
    const good = patients.filter((p) => p.rate >= 80).length;
    const fair = patients.filter((p) => p.rate >= 60 && p.rate < 80).length;
    const risk = patients.filter((p) => p.rate < 60).length;
    new Chart(canvas.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: ["Good ≥80%", "Fair 60–79%", "At Risk <60%"],
        datasets: [
          {
            data: [good, fair, risk],
            backgroundColor: [
              "rgba(93,172,150,0.85)",
              "rgba(217,138,42,0.85)",
              "rgba(217,79,79,0.85)",
            ],
            borderColor: "#FFFFFF",
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1B5271",
            titleColor: "#FFFFFF",
            bodyColor: "#9DD1C2",
          },
        },
      },
    });
  } catch (e) {
    /* non-critical */
  }
}

/* Doctor-side medicine requests preview — read-only via GET /requests
   (doctors can view, but only pharmacists can reply/fulfill). */
async function fetchAllRequests() {
  try {
    return await api("GET", "/requests");
  } catch {
    return [];
  }
}
async function renderDrRequests() {
  const container = document.getElementById("drReqList");
  if (!container) return;
  const reqs = (await fetchAllRequests())
    .slice()
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const countEl = document.getElementById("reqCount");
  if (countEl)
    countEl.textContent = `${reqs.length} request${reqs.length !== 1 ? "s" : ""}`;
  if (!reqs.length) {
    container.innerHTML = `<div style="padding:40px;text-align:center;color:#7A9CA8;font-size:0.875rem;">No medicine requests yet.</div>`;
    return;
  }
  const stMap = {
    pending: { clr: "#A0620A", bg: "#FBF0DC" },
    replied: { clr: "#1A6496", bg: "#DCF0FA" },
    fulfilled: { clr: "#1E8A65", bg: "#D5F3EB" },
    unavailable: { clr: "#B03030", bg: "#FAE8E8" },
  };
  container.innerHTML = reqs
    .map((r) => {
      const st = stMap[r.status] || { clr: "#7A9CA8", bg: "#EDF5F2" };
      return `<div style="padding:16px 20px;border-bottom:1px solid #D1E4DE;display:flex;gap:14px;align-items:flex-start;">
      <div style="width:40px;height:40px;border-radius:11px;background:${st.bg};display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">💊</div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
          <span style="font-weight:700;color:#1B5271;font-size:0.92rem;">${r.patient_name || "Patient"}</span>
          <span style="font-size:0.68rem;font-weight:800;letter-spacing:0.05em;text-transform:uppercase;color:${st.clr};background:${st.bg};padding:2px 9px;border-radius:100px;">${r.status}</span>
          <span style="font-size:0.70rem;color:#7A9CA8;margin-left:auto;">${timeAgo(r.created_at)}</span>
        </div>
        <div style="font-size:0.88rem;font-weight:700;color:#3A5563;">${r.medicine_name}${r.dosage ? '<span style="color:#7A9CA8;font-weight:400;"> · ' + r.dosage + "</span>" : ""}</div>
        <div style="font-size:0.78rem;color:#7A9CA8;margin-top:3px;">${r.message || ""}</div>
      </div>
    </div>`;
    })
    .join("");
}
async function renderDrOverviewReqs() {
  const container = document.getElementById("drOverviewReqs");
  if (!container) return;
  const reqs = (await fetchAllRequests())
    .filter((r) => r.status === "pending")
    .slice(0, 4);
  if (!reqs.length) {
    container.innerHTML =
      '<p style="font-size:0.80rem;color:#7A9CA8;text-align:center;padding:12px;">No pending requests.</p>';
    return;
  }
  container.innerHTML = reqs
    .map(
      (r) => `
    <div style="display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid #D1E4DE;">
      <span style="font-size:0.9rem;">💊</span>
      <div style="flex:1;min-width:0;"><div style="font-weight:600;font-size:0.80rem;color:#1B5271;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${r.patient_name} — ${r.medicine_name}</div><div style="font-size:0.70rem;color:#7A9CA8;">${timeAgo(r.created_at)}</div></div>
      <span style="font-size:0.65rem;font-weight:800;color:#A0620A;background:#FBF0DC;padding:2px 8px;border-radius:100px;white-space:nowrap;">pending</span>
    </div>`,
    )
    .join("");
}
async function updateDrReqBadge() {
  const n = (await fetchAllRequests()).filter(
    (r) => r.status === "pending",
  ).length;
  const b = document.getElementById("drReqBadge");
  if (b) {
    b.textContent = n;
    b.style.display = n > 0 ? "inline-flex" : "none";
  }
}

/* ════════════════════════════════════════════════════════════════
   [Q] GLOBAL INIT
════════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  if (path.includes("portal")) initPortal();
  else if (path.includes("patient-dashboard")) initPatientDashboard();
  else if (path.includes("doctor-dashboard")) initDoctorDashboard();

  document.querySelectorAll(".nav-link").forEach((l) => {
    const href = l.getAttribute("href");
    if (href && window.location.pathname.endsWith(href))
      l.classList.add("active-link");
  });
  document
    .querySelectorAll("[data-logout]")
    .forEach((btn) => btn.addEventListener("click", handleLogout));
  document.querySelectorAll(".dt-modal-overlay,.forgot-overlay").forEach((ov) =>
    ov.addEventListener("click", (e) => {
      if (e.target === ov) {
        ov.classList.remove("open");
        document.body.style.overflow = "";
      }
    }),
  );

  const td = document.getElementById("todayDate");
  if (td)
    td.textContent = new Date().toLocaleDateString("en-KE", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  const tdp = document.getElementById("todayDatePat");
  if (tdp)
    tdp.textContent = new Date().toLocaleDateString("en-KE", {
      weekday: "short",
      day: "numeric",
      month: "long",
      year: "numeric",
    });

  document.getElementById("review-btn")?.addEventListener("click", () => {
    switchDocTab?.("tab-atrisk", document.querySelectorAll(".sidebar-link")[2]);
  });

  document.querySelectorAll(".mobile-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".mobile-tab-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      (window.switchDashTab || window.switchDocTab)?.(btn.dataset.tab);
    });
  });
});

function validateForm() {
  const name = document.getElementById("name")?.value.trim();
  const email = document.getElementById("email")?.value.trim();
  if (!name || !email) {
    showToast("Please fill required fields.", "error");
    return false;
  }
  showToast("Inquiry submitted! We'll respond within 24 hours.");
  return false;
}
