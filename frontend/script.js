/* script.js — frontend with reviews, rating display, category filter, verify */
(() => {
  const API_RESOURCES = "/api/resources";
  const API_ADD = "/api/resource";
  const API_REVIEWS_LIST = id => `/api/resource/${id}/reviews`;
  const API_ADD_REVIEW = id => `/api/resource/${id}/review`;
  const API_VERIFY = id => `/api/resource/${id}/verify`;

  // elements
  const listEl = () => document.getElementById("list");
  const noResultsEl = () => document.getElementById("noResults");
  const searchInput = document.getElementById("searchInput");
  const searchBtn = document.getElementById("searchBtn");
  const categoryFilter = document.getElementById("categoryFilter");
  const clearFilters = document.getElementById("clearFilters");
  const addForm = document.getElementById("addForm");
  const reviewForm = document.getElementById("reviewForm");
  const reviewsList = document.getElementById("reviewsList");
  const reviewsModal = new bootstrap.Modal(document.getElementById("reviewsModal"));
  const locateBtn = document.getElementById("locateBtn");

  let map, markersLayer, allResources = [], activeResourceId = null;

  function initMap(){
    map = L.map("map").setView([13.0827, 80.2707], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    markersLayer = L.layerGroup().addTo(map);

    map.on("click", e => {
      const lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
      const latInput = document.querySelector("input[name='latitude']");
      const lngInput = document.querySelector("input[name='longitude']");
      if (latInput && document.getElementById("addModal").classList.contains("show")) {
        latInput.value = lat; lngInput.value = lng;
      } else {
        L.popup().setLatLng(e.latlng).setContent(`<div style="min-width:180px">Coordinates:<br/><strong>${lat}, ${lng}</strong><div style="margin-top:6px"><button id="useCoordBtn" class="btn btn-sm btn-accent">Use in form</button></div></div>`).openOn(map);
        setTimeout(()=> {
          const b = document.getElementById("useCoordBtn");
          if (b) {
            b.addEventListener("click", () => {
              const bs = new bootstrap.Modal(document.getElementById("addModal"));
              bs.show();
              document.querySelector("input[name='latitude']").value = lat;
              document.querySelector("input[name='longitude']").value = lng;
              map.closePopup();
            });
          }
        }, 10);
      }
    });
  }

  async function loadResources() {
    const q = searchInput.value.trim();
    const cat = categoryFilter.value;
    const params = new URLSearchParams();
    if (cat) params.set("category", cat);
    if (q) params.set("q", q);
    try {
      const res = await fetch(API_RESOURCES + (params.toString() ? "?" + params.toString() : ""));
      const data = await res.json();
      allResources = Array.isArray(data) ? data : [];
      renderResources(allResources);
      placeMarkers(allResources);
    } catch (e) {
      console.error(e);
      listEl().innerHTML = "<div class='text-muted p-3'>Failed to load resources</div>";
    }
  }

  function renderResources(arr) {
    const container = listEl();
    container.innerHTML = "";
    if (!arr.length) { noResultsEl().classList.remove("d-none"); return; }
    noResultsEl().classList.add("d-none");
    arr.forEach(r => {
      const col = document.createElement("div"); col.className = "col-12";
      const rating = renderStars(r.avg_rating);
      const verified = r.verified ? '<span class="badge bg-success ms-2">Verified</span>' : '';
      col.innerHTML = `
        <div class="p-3 resource-card rounded">
          <div class="d-flex justify-content-between">
            <div>
              <div style="font-weight:600">${escapeHtml(r.name || "")} ${verified}</div>
              <div class="small-muted">${escapeHtml(r.category || "")} ${r.address ? " • " + escapeHtml(r.address) : ""}</div>
              <div class="small-muted mt-1">${rating}</div>
            </div>
            <div class="text-end">
              <button class="btn btn-sm btn-outline-secondary mb-1 viewBtn" data-id="${r._id || r.id}"><i class="fa-solid fa-comment-dots"></i></button>
              <button class="btn btn-sm btn-outline-secondary mb-1 verifyBtn" data-id="${r._id || r.id}"><i class="fa-solid fa-check"></i></button>
            </div>
          </div>
        </div>`;
      container.appendChild(col);
    });
    // attach listeners
    container.querySelectorAll(".viewBtn").forEach(b => b.addEventListener("click", ev => {
      const id = ev.currentTarget.dataset.id; openReviews(id);
    }));
    container.querySelectorAll(".verifyBtn").forEach(b => b.addEventListener("click", ev => {
      const id = ev.currentTarget.dataset.id; doVerify(id);
    }));
  }

  function renderStars(avg){
    if (!avg && avg !== 0) return "";
    const a = Math.round(avg * 2) / 2; // round 0.5
    let out = "";
    for (let i=1;i<=5;i++){
      if (i <= Math.floor(a)) out += '<i class="fa-solid fa-star" style="color:#f5c518"></i>';
      else if (i - 0.5 === a) out += '<i class="fa-solid fa-star-half-stroke" style="color:#f5c518"></i>';
      else out += '<i class="fa-regular fa-star" style="color:#ddd"></i>';
    }
    out += ` <span class="small-muted">(${Number(avg).toFixed(1)})</span>`;
    return out;
  }

  function clearMarkers(){ markersLayer.clearLayers(); }

  function placeMarkers(arr){
    clearMarkers();
    arr.forEach(r => {
      const lat = Number(r.latitude || r.lat || r.latitude);
      const lon = Number(r.longitude || r.lon || r.longitude);
      if (!isFinite(lat) || !isFinite(lon)) return;
      const marker = L.marker([lat, lon]).addTo(markersLayer);
      const avg = r.avg_rating ? ` — ${Number(r.avg_rating).toFixed(1)} ★` : "";
      marker.bindPopup(`<strong>${escapeHtml(r.name||"")}</strong><br/><small>${escapeHtml(r.address||"") || ""}${avg}</small><br/><div style="margin-top:6px"><button class="btn btn-sm btn-outline-primary popupReviews" data-id="${r._id || r.id}">Reviews</button></div>`, {maxWidth:250});
      marker.on("popupopen", (e) => {
        setTimeout(()=> {
          const b = document.querySelector(".popupReviews");
          if (b) b.addEventListener("click", ()=> openReviews(b.dataset.id));
        }, 10);
      });
    });
  }

  function escapeHtml(s){ return (s||"").toString().replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[m])); }

  // Reviews
  async function openReviews(id) {
    activeResourceId = id;
    document.getElementById("reviewsTitle").textContent = "Reviews";
    reviewsList.innerHTML = "<div class='small-muted p-2'>Loading...</div>";
    reviewForm.reset();
    try {
      const res = await fetch(API_REVIEWS_LIST(id));
      const data = await res.json();
      if (!Array.isArray(data) || !data.length) {
        reviewsList.innerHTML = "<div class='small-muted p-2'>No reviews yet.</div>";
      } else {
        reviewsList.innerHTML = data.map(r => `<div class="mb-2"><strong>${escapeHtml(r.user_name||'Anonymous')}</strong> <span class="small-muted"> - ${new Date((r.created_at||0)*1000).toLocaleString()}</span><div>${renderStars(r.rating)}</div><div class="small-muted">${escapeHtml(r.comment||'')}</div></div>`).join("");
      }
    } catch (e) {
      console.error(e); reviewsList.innerHTML = "<div class='text-danger p-2'>Failed to load reviews</div>";
    }
    reviewsModal.show();
  }

  // submit review
  reviewForm?.addEventListener("submit", async (ev)=> {
    ev.preventDefault();
    if (!activeResourceId) return alert("No resource selected");
    const fm = new FormData(reviewForm);
    const body = Object.fromEntries(fm.entries());
    try {
      const res = await fetch(API_ADD_REVIEW(activeResourceId), {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
      if (res.ok) {
        alert("Review added"); reviewsModal.hide(); await loadResources();
      } else {
        const out = await res.json(); alert(out.error || out.message || "Failed to add review");
      }
    } catch (e) { console.error(e); alert("Network error"); }
  });

  // verify (admin token prompt)
  async function doVerify(id) {
    const token = prompt("Enter admin token to verify this resource (leave blank to cancel):");
    if (!token) return;
    try {
      const res = await fetch(API_VERIFY(id), {method:"POST", headers:{"X-ADMIN-TOKEN": token}});
      if (res.ok) { alert("Resource verified"); await loadResources(); }
      else { const out = await res.json(); alert(out.error||"Unauthorized"); }
    } catch (e) { console.error(e); alert("Network error"); }
  }

  // Add resource
  addForm?.addEventListener("submit", async (ev)=> {
    ev.preventDefault();
    const fm = new FormData(addForm);
    const body = Object.fromEntries(fm.entries());
    if (!body.name || !body.latitude || !body.longitude) return alert("Name and coordinates required");
    try {
      const res = await fetch(API_ADD, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
      if (res.ok) { alert("Added"); addForm.reset(); bootstrap.Modal.getInstance(document.getElementById("addModal")).hide(); await loadResources(); }
      else { const out = await res.json(); alert(out.error||"Failed"); }
    } catch (e) { console.error(e); alert("Network error"); }
  });

  // UI bindings
  function attachUI(){
    document.getElementById("searchBtn").addEventListener("click", loadResources);
    searchInput.addEventListener("keyup", (e)=> { if (e.key==="Enter") loadResources(); });
    categoryFilter.addEventListener("change", loadResources);
    clearFilters.addEventListener("click", ()=> { searchInput.value=""; categoryFilter.value=""; loadResources(); });
    locateBtn.addEventListener("click", ()=> {
      if (!navigator.geolocation) return alert("Geolocation not supported");
      navigator.geolocation.getCurrentPosition(p => map.setView([p.coords.latitude,p.coords.longitude],14), ()=> alert("Failed to get location"));
    });
  }

  // init
  document.addEventListener("DOMContentLoaded", async ()=> {
    initMap(); attachUI(); await loadResources();
  });

})();
