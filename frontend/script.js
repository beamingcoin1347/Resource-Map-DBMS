/* improved script.js — robust loading, debounce search, spinner & count */
(() => {
  const API_RESOURCES = "/api/resources";
  const API_ADD = "/api/resource";

  // DOM refs
  const listEl = () => document.getElementById("list");
  const noResultsEl = () => document.getElementById("noResults");
  const searchInput = document.getElementById("searchInput");
  const searchBtn = document.getElementById("searchBtn");
  const categoryFilter = document.getElementById("categoryFilter");
  const clearFilters = document.getElementById("clearFilters");
  const locateBtn = document.getElementById("locateBtn");
  const openAddBtn = document.getElementById("openAddBtn");

  let map, markersLayer, allResources = [];

  function setLoading(on) {
    const sidebar = document.querySelector('.sidebar');
    if (on) {
      sidebar.style.opacity = 0.6;
    } else {
      sidebar.style.opacity = 1;
    }
  }

  function debounce(fn, wait=300){
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(()=>fn(...args), wait);
    };
  }

  function initMap(){
    map = L.map("map", { zoomControl:true }).setView([13.0827,80.2707], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom:19 }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
    map.on("click", e => {
      const lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
      // if modal open fill fields
      const latInput = document.querySelector("input[name='latitude']");
      const lngInput = document.querySelector("input[name='longitude']");
      if (latInput && document.getElementById('addModal')?.classList.contains('show')){
        latInput.value = lat; lngInput.value = lng;
      }
    });
  }

  async function loadResources(){
    setLoading(true);
    try {
      const res = await fetch(API_RESOURCES);
      if (!res.ok) throw new Error("Network response not ok");
      const json = await res.json();
      allResources = Array.isArray(json) ? json : [];
      renderResources(allResources);
      placeMarkers(allResources);
    } catch (e) {
      console.error("loadResources failed", e);
      listEl().innerHTML = "<div class='no-results'>Failed to load resources</div>";
      noResultsEl().classList.add("d-none");
    } finally {
      setLoading(false);
    }
  }

  function renderResources(arr){
    const container = listEl();
    container.innerHTML = "";
    if (!arr.length) {
      noResultsEl().classList.remove("d-none");
      return;
    }
    noResultsEl().classList.add("d-none");
    arr.forEach(r => {
      const div = document.createElement("div");
      div.className = "col-12";
      div.innerHTML = `
        <div class="p-3 resource-card rounded">
          <div style="font-weight:600">${escapeHtml(r.name || "Untitled")}</div>
          <div class="small-muted">${escapeHtml(r.category || "")} ${r.address? " • " + escapeHtml(r.address): ""}</div>
        </div>`;
      div.addEventListener("click", ()=> {
        if (r.latitude && r.longitude) map.setView([parseFloat(r.latitude), parseFloat(r.longitude)], 15);
      });
      container.appendChild(div);
    });
  }

  function clearMarkers(){
    markersLayer.clearLayers();
  }

  function placeMarkers(arr){
    clearMarkers();
    arr.forEach(r => {
      if (!r.latitude || !r.longitude) return;
      const lat = Number(r.latitude), lon = Number(r.longitude);
      if (!isFinite(lat) || !isFinite(lon)) return;
      const mk = L.marker([lat, lon]).addTo(markersLayer);
      mk.bindPopup(`<strong>${escapeHtml(r.name||"")}</strong><br/><small>${escapeHtml(r.address||"")}</small>`);
    });
  }

  function applyFilters(){
    const q = (searchInput.value || "").trim().toLowerCase();
    const cat = (categoryFilter.value || "").trim().toLowerCase();
    const filtered = allResources.filter(r => {
      const name = (r.name||"").toLowerCase();
      const addr = (r.address||"").toLowerCase();
      const rc = (r.category||"").toLowerCase();
      const okQ = !q || name.includes(q) || addr.includes(q);
      const okC = !cat || rc === cat;
      return okQ && okC;
    });
    renderResources(filtered);
    placeMarkers(filtered);
  }

  function escapeHtml(s){ return (s||"").toString().replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[m])); }

  async function submitAddForm(ev){
    ev.preventDefault();
    const form = ev.target;
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.name || !data.latitude || !data.longitude){ alert("Please enter name, latitude and longitude"); return; }
    data.latitude = Number(data.latitude); data.longitude = Number(data.longitude);
    try {
      const r = await fetch(API_ADD, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) });
      const out = await r.json();
      if (r.ok){ 
        bootstrap.Modal.getInstance(document.getElementById("addModal")).hide();
        form.reset(); 
        await loadResources();
      } else {
        alert(out.error || out.message || "Failed to add resource");
      }
    } catch (e) {
      console.error(e);
      alert("Network error while adding resource");
    }
  }

  function attachUI(){
    document.getElementById("addForm").addEventListener("submit", submitAddForm);
    document.getElementById("searchBtn").addEventListener("click", applyFilters);
    searchInput.addEventListener("input", debounce(applyFilters, 300));
    categoryFilter.addEventListener("change", applyFilters);
    clearFilters.addEventListener("click", ()=>{ searchInput.value=""; categoryFilter.value=""; applyFilters(); });
    locateBtn.addEventListener("click", ()=> {
      if (!navigator.geolocation) return alert("Geolocation not supported");
      navigator.geolocation.getCurrentPosition(p => { map.setView([p.coords.latitude, p.coords.longitude], 14); }, ()=> alert("Failed to get location"));
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    initMap();
    attachUI();
    await loadResources();
  });

})();
