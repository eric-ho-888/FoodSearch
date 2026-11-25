/* FoodSearch — progressive enhancement.
 * The server renders a complete page; this script upgrades it to live search
 * by re-fetching the same URL and swapping in the results region.
 * With JS disabled, the search form and category chips still work normally.
 */
(function () {
  "use strict";

  var app = document.getElementById("app");
  var results = document.getElementById("results");
  var form = document.getElementById("search-form");
  if (!app || !results || !form) return;

  var input = document.getElementById("q");
  // These live inside the toolbar, which is re-rendered after every search.
  var sortSelect, openToggle, locateBtn;

  var state = {
    q: app.dataset.q || "",
    category: app.dataset.category || "All",
    region: app.dataset.region || "All",
    sort: app.dataset.sort || "relevance",
    open: app.dataset.open === "1",
    lat: app.dataset.lat || "",
    lng: app.dataset.lng || ""
  };

  var controller = null;
  var debounceTimer = null;
  var requestSeq = 0;

  function buildUrl() {
    var params = new URLSearchParams();
    if (state.q) params.set("q", state.q);
    if (state.category && state.category !== "All") params.set("category", state.category);
    if (state.region && state.region !== "All") params.set("region", state.region);
    if (state.sort && state.sort !== "relevance") params.set("sort", state.sort);
    if (state.open) params.set("open", "1");
    if (state.lat && state.lng) {
      params.set("lat", state.lat);
      params.set("lng", state.lng);
    }
    var qs = params.toString();
    return "/" + (qs ? "?" + qs : "");
  }

  function syncControls() {
    document.querySelectorAll(".chip-cat").forEach(function (chip) {
      chip.classList.toggle("is-active", (chip.dataset.category || "All") === state.category);
    });
    document.querySelectorAll(".region-tab").forEach(function (tab) {
      var active = (tab.dataset.region || "All") === state.region;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (sortSelect) sortSelect.value = state.sort;
    if (openToggle) openToggle.checked = state.open;
  }

  function setBusy(busy) {
    results.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function refresh(mode) {
    if (controller) controller.abort();
    controller = new AbortController();
    var seq = ++requestSeq;
    var url = buildUrl();

    setBusy(true);
    syncControls();

    fetch(url, {
      signal: controller.signal,
      headers: { "X-Requested-With": "fetch" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.text();
      })
      .then(function (html) {
        if (seq !== requestSeq) return;
        var doc = new DOMParser().parseFromString(html, "text/html");
        var nextResults = doc.getElementById("results");
        var nextToolbar = doc.querySelector(".toolbar");
        var nextBanner = doc.querySelector(".banner");
        if (!nextResults) return;

        results.innerHTML = nextResults.innerHTML;

        // The toolbar carries the result count, region tab counts and active tab,
        // so swap the whole block rather than patching pieces of it.
        var currentToolbar = document.querySelector(".toolbar");
        if (currentToolbar && nextToolbar) {
          currentToolbar.replaceWith(nextToolbar);
          bindControls();
        }
        var currentBanner = document.querySelector(".banner");
        if (nextBanner) {
          if (currentBanner) currentBanner.replaceWith(nextBanner);
          else document.querySelector(".toolbar").after(nextBanner);
        } else if (currentBanner) {
          currentBanner.remove();
        }

        app.dataset.q = state.q;
        app.dataset.category = state.category;
        app.dataset.region = state.region;
        app.dataset.sort = state.sort;
        app.dataset.open = state.open ? "1" : "0";
        app.dataset.lat = state.lat;
        app.dataset.lng = state.lng;

        var historyMethod = mode === "submit" ? "pushState" : "replaceState";
        window.history[historyMethod]({ fsearch: state }, "", url);
      })
      .catch(function (error) {
        if (error && error.name === "AbortError") return;
        // Fall back to a normal navigation so the user still gets results.
        window.location.assign(url);
      })
      .then(function () {
        if (seq === requestSeq) setBusy(false);
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    state.q = input ? input.value.trim() : "";
    refresh("submit");
  });

  if (input) {
    input.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        var value = input.value.trim();
        if (value === state.q) return;
        state.q = value;
        refresh("replace");
      }, 260);
    });
    // Enter inside the field should feel instant.
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") clearTimeout(debounceTimer);
    });
  }

  document.querySelectorAll(".suggestion").forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      var term = link.dataset.q || link.textContent.trim();
      if (input) input.value = term;
      state.q = term;
      refresh("submit");
      if (input) input.focus();
    });
  });

  document.querySelectorAll(".chip-cat").forEach(function (chip) {
    chip.addEventListener("click", function (event) {
      event.preventDefault();
      state.category = chip.dataset.category || "All";
      refresh("submit");
    });
  });

  function bindControls() {
    sortSelect = document.getElementById("sort");
    openToggle = document.getElementById("open-toggle");
    locateBtn = document.getElementById("locate-btn");

    document.querySelectorAll(".region-tab").forEach(function (tab) {
      if (tab.dataset.bound) return;
      tab.dataset.bound = "1";
      tab.addEventListener("click", function (event) {
        event.preventDefault();
        state.region = tab.dataset.region || "All";
        refresh("submit");
      });
    });

    if (sortSelect && !sortSelect.dataset.bound) {
      sortSelect.dataset.bound = "1";
      sortSelect.addEventListener("change", function () {
        state.sort = sortSelect.value;
        refresh("submit");
      });
    }

    if (openToggle && !openToggle.dataset.bound) {
      openToggle.dataset.bound = "1";
      openToggle.addEventListener("change", function () {
        state.open = openToggle.checked;
        refresh("submit");
      });
    }

    if (locateBtn && !locateBtn.dataset.bound) {
      locateBtn.dataset.bound = "1";
      bindLocate(locateBtn);
    }
  }

  function bindLocate(locateBtn) {
    locateBtn.addEventListener("click", function () {
      if (!("geolocation" in navigator)) {
        window.location.assign("/?q=" + encodeURIComponent(state.q));
        return;
      }
      var original = locateBtn.textContent;
      locateBtn.disabled = true;
      locateBtn.textContent = "Locating…";
      navigator.geolocation.getCurrentPosition(
        function (position) {
          state.lat = position.coords.latitude.toFixed(5);
          state.lng = position.coords.longitude.toFixed(5);
          state.sort = "distance";
          locateBtn.disabled = false;
          locateBtn.textContent = original;
          refresh("submit");
        },
        function () {
          locateBtn.disabled = false;
          locateBtn.textContent = "Location unavailable";
          setTimeout(function () { locateBtn.textContent = original; }, 2500);
        },
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 }
      );
    });
  }

  bindControls();

  window.addEventListener("popstate", function (event) {
    var next = event.state && event.state.fsearch ? event.state.fsearch : null;
    var params = new URLSearchParams(window.location.search);
    state.q = next ? next.q : (params.get("q") || "");
    state.category = next ? next.category : (params.get("category") || "All");
    state.region = next ? next.region : (params.get("region") || "All");
    state.sort = next ? next.sort : (params.get("sort") || "relevance");
    state.open = next ? !!next.open : params.get("open") === "1";
    state.lat = next ? next.lat : (params.get("lat") || "");
    state.lng = next ? next.lng : (params.get("lng") || "");
    if (input) input.value = state.q;
    refresh("replace");
  });
})();