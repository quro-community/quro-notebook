(function () {
  "use strict";

  var APP = (window.__quro_notebook__ = window.__quro_notebook__ || {});

  var state = {
    pages: [],
    activeDocId: null,
    view: "list",
    theme: localStorage.getItem("quro-theme") || "light",
  };

  APP.getState = function () {
    return state;
  };

  APP.navigateTo = function (docId) {
    if (state.activeDocId === docId && state.view === "article") return;
    state.activeDocId = docId;
    state.view = "article";
    window.location.hash = docId;
    renderArticle(docId);
  };

  APP.showResults = function (results) {
    if (results.length === 0) {
      renderSearchEmpty();
      return;
    }
    state.view = "search";
    state.activeDocId = null;
    renderSearchResults(results);
  };

  APP.showPageList = function () {
    state.view = "list";
    state.activeDocId = null;
    renderArticleList();
  };

  APP.backToList = function () {
    state.view = "list";
    state.activeDocId = null;
    window.location.hash = "";
    renderArticleList();
  };

  /* ── Render: Article List (Homepage) ── */
  function renderArticleList() {
    var content = document.getElementById("content");
    if (!content) return;

    var pages = state.pages;
    if (!pages || pages.length === 0) {
      content.innerHTML =
        '<div class="empty-state">' +
        '<p>No articles yet — run the build first</p>' +
        "</div>";
      return;
    }

    var sorted = pages.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    });

    var cardsHtml = sorted
      .map(function (p) {
        var title = escapeHtml(p.title || p.doc_id);
        var date = formatDate(p.created_at);
        var summary = escapeHtml(p.summary || "");
        var tagsHtml = (p.tags || [])
          .slice(0, 4)
          .map(function (t) {
            return '<span class="tag">' + escapeHtml(t) + "</span>";
          })
          .join("");

        return (
          '<article class="article-card" data-doc-id="' +
          escapeAttr(p.doc_id) +
          '" role="link" tabindex="0">' +
          '<div class="article-card-header">' +
          '<h2 class="article-card-title">' +
          title +
          "</h2>" +
          '<time class="article-card-date" datetime="' +
          escapeAttr(p.created_at || "") +
          '">' +
          date +
          "</time>" +
          "</div>" +
          (summary
            ? '<p class="article-card-summary">' + summary + "</p>"
            : "") +
          (tagsHtml.length
            ? '<div class="article-card-meta">' +
              '<div class="article-card-tags">' +
              tagsHtml +
              "</div>" +
              "</div>"
            : "") +
          "</article>"
        );
      })
      .join("");

    var totalCount = pages.length;
    content.innerHTML =
      '<div class="article-list">' +
      '<header class="article-list-header">' +
      '<h1 class="article-list-title">Articles</h1>' +
      '<p class="article-list-subtitle">' +
      totalCount +
      " article" +
      (totalCount !== 1 ? "s" : "") +
      "</p>" +
      "</header>" +
      '<div class="article-cards">' +
      cardsHtml +
      "</div>" +
      "</div>";

    var cards = content.querySelectorAll(".article-card");
    cards.forEach(function (card) {
      card.addEventListener("click", function () {
        var docId = card.getAttribute("data-doc-id");
        if (docId) APP.navigateTo(docId);
      });
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          var docId = card.getAttribute("data-doc-id");
          if (docId) APP.navigateTo(docId);
        }
      });
    });
  }

  /* ── Render: Article View ── */
  function renderArticle(docId) {
    var content = document.getElementById("content");
    if (!content) return;

    content.innerHTML =
      '<div class="loading">Loading article...</div>';

    var pageData = findPage(docId);

    var inlineEl = document.getElementById("quro-page-" + docId);
    if (inlineEl) {
      var html;
      if (inlineEl.getAttribute("data-encoding") === "base64") {
        var b64 = inlineEl.textContent.trim();
        var binary = atob(b64);
        var bytes = new Uint8Array(binary.length);
        for (var i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        html = new TextDecoder("utf-8").decode(bytes);
      } else {
        html = inlineEl.textContent;
      }
      showArticle(content, docId, html, pageData);
      return;
    }

    fetch("pages/" + encodeURIComponent(docId) + ".html")
      .then(function (resp) {
        if (!resp.ok) throw new Error("Not found");
        return resp.text();
      })
      .then(function (html) {
        showArticle(content, docId, html, pageData);
      })
      .catch(function () {
        content.innerHTML =
          '<div class="empty-state">' +
          '<p>Article not found.</p>' +
          '<a class="back-link" id="back-link-fallback">&#8592; Back to articles</a>' +
          "</div>";
        var backLink = document.getElementById("back-link-fallback");
        if (backLink)
          backLink.addEventListener("click", APP.backToList);
      });
  }

  function showArticle(content, docId, html, pageData) {
    var backBtn =
      '<button class="back-link" aria-label="Back to articles">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>' +
      "Articles" +
      "</button>";

    content.innerHTML =
      '<div class="article-view">' +
      backBtn +
      html +
      "</div>";

    var backLink = content.querySelector(".back-link");
    if (backLink) {
      backLink.addEventListener("click", function () {
        APP.backToList();
      });
    }

    activateAskAi();
    highlightActiveToc();

    var tocLinks = content.querySelectorAll(".page-toc a");
    tocLinks.forEach(function (link) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        var targetId = link.getAttribute("href").slice(1);
        var target = document.getElementById(targetId);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
          window.location.hash = targetId;
        }
      });
    });

    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function findPage(docId) {
    return state.pages.find(function (p) {
      return p.doc_id === docId;
    });
  }

  /* ── Render: Search Results ── */
  function renderSearchResults(results) {
    var content = document.getElementById("content");
    if (!content) return;

    var resultsHtml = results
      .map(function (r) {
        var title = escapeHtml(r.title || r.doc_id || "");
        var snippet = escapeHtml(r.snippet || "");
        return (
          '<div class="search-result-item" data-doc-id="' +
          escapeAttr(r.doc_id) +
          '" role="link" tabindex="0">' +
          '<div class="search-result-title">' +
          title +
          "</div>" +
          (snippet
            ? '<div class="search-result-snippet">' +
              snippet +
              "</div>"
            : "") +
          "</div>"
        );
      })
      .join("");

    content.innerHTML =
      '<div class="search-results">' +
      '<p class="search-results-header">' +
      results.length +
      " result" +
      (results.length !== 1 ? "s" : "") +
      "</p>" +
      resultsHtml +
      "</div>";

    var items = content.querySelectorAll(".search-result-item");
    items.forEach(function (item) {
      item.addEventListener("click", function () {
        var docId = item.getAttribute("data-doc-id");
        if (docId) APP.navigateTo(docId);
      });
      item.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          var docId = item.getAttribute("data-doc-id");
          if (docId) APP.navigateTo(docId);
        }
      });
    });
  }

  function renderSearchEmpty() {
    var content = document.getElementById("content");
    if (!content) return;
    content.innerHTML =
      '<div class="search-results">' +
      '<p class="search-results-header">No results found</p>' +
      "</div>";
  }

  /* ── Table of Contents Highlight ── */
  function highlightActiveToc() {
    var tocLinks = document.querySelectorAll(".toc-item a");
    var headings = [];
    document
      .querySelectorAll(".markdown-body h2, .markdown-body h3")
      .forEach(function (h) {
        headings.push(h);
      });

    if (headings.length === 0) return;

    var onScroll = (function () {
      var ticking = false;
      return function () {
        if (!ticking) {
          requestAnimationFrame(function () {
            var scrollY = window.scrollY || window.pageYOffset;
            var activeId = null;
            for (var i = headings.length - 1; i >= 0; i--) {
              if (headings[i].offsetTop - 100 <= scrollY) {
                activeId = headings[i].getAttribute("id");
                break;
              }
            }
            tocLinks.forEach(function (link) {
              var href = link.getAttribute("href");
              if (href === "#" + activeId) {
                link.classList.add("active");
              } else {
                link.classList.remove("active");
              }
            });
            ticking = false;
          });
          ticking = true;
        }
      };
    })();

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ── Ask AI ── */
  function activateAskAi() {
    var btns = document.querySelectorAll(".btn-ask-ai");
    btns.forEach(function (btn) {
      if (btn.dataset.quroBound) return;
      btn.dataset.quroBound = "1";

      btn.addEventListener("click", function () {
        var article = document.querySelector(".notebook-page");
        if (!article) return;

        var pageText = article.querySelector(".markdown-body");
        var textContent = pageText ? pageText.textContent || "" : "";

        if (textContent.trim()) {
          navigator.clipboard
            .writeText(textContent.trim())
            .then(function () {
              showToast("Content copied — paste into your AI chat");
            })
            .catch(function () {
              showToast("Could not copy content");
            });
        }
      });
    });
  }

  /* ── Toast ── */
  function showToast(message) {
    var toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(function () {
      toast.classList.add("hidden");
    }, 3000);
  }

  /* ── Theme Toggle ── */
  function initTheme() {
    document.documentElement.setAttribute("data-theme", state.theme);
    updateThemeIcon();

    var toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        state.theme = state.theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", state.theme);
        localStorage.setItem("quro-theme", state.theme);
        updateThemeIcon();
      });
    }
  }

  function updateThemeIcon() {
    var sun = document.getElementById("theme-icon-sun");
    var moon = document.getElementById("theme-icon-moon");
    if (!sun || !moon) return;
    if (state.theme === "dark") {
      sun.style.display = "none";
      moon.style.display = "";
    } else {
      sun.style.display = "";
      moon.style.display = "none";
    }
  }

  /* ── Helpers ── */
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  function escapeAttr(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr.substring(0, 10);
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  /* ── Init ── */
  function loadIndex() {
    var inlineEl = document.getElementById("quro-index-data");
    if (inlineEl) {
      try {
        var data = JSON.parse(inlineEl.textContent);
        state.pages = data.pages || [];
        onIndexReady();
        return;
      } catch (e) {
        /* fall through to fetch */
      }
    }

    fetch("data/index.json")
      .then(function (resp) {
        if (!resp.ok) throw new Error("Index not found");
        return resp.json();
      })
      .then(function (index) {
        state.pages = index.pages || [];
        onIndexReady();
      })
      .catch(function () {
        var content = document.getElementById("content");
        if (content) {
          content.innerHTML =
            '<div class="empty-state">' +
            '<p>No index found &mdash; run the build first</p>' +
            "</div>";
        }
      });
  }

  function onIndexReady() {
    var hash = window.location.hash.slice(1);
    if (hash) {
      var pageData = findPage(hash);
      if (pageData) {
        APP.navigateTo(hash);
      } else {
        APP.showPageList();
      }
    } else {
      APP.showPageList();
    }
  }

  function init() {
    initTheme();
    loadIndex();

    window.addEventListener("hashchange", function () {
      var docId = window.location.hash.slice(1);
      if (docId) {
        var pageData = findPage(docId);
        if (pageData) {
          APP.navigateTo(docId);
        }
      } else {
        APP.backToList();
      }
    });

    var searchInput = document.getElementById("search-input");
    if (searchInput) {
      var debounceTimer;
      searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        var query = searchInput.value.trim();
        if (!query) {
          APP.showPageList();
          return;
        }
        debounceTimer = setTimeout(function () {
          if (APP.search) {
            APP.search(query);
          }
        }, 300);
      });
    }

    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== searchInput) {
        e.preventDefault();
        if (searchInput) searchInput.focus();
      }
      if (e.key === "Escape" && document.activeElement === searchInput) {
        searchInput.blur();
        searchInput.value = "";
        APP.showPageList();
      }
    });

    var navBrand = document.getElementById("nav-brand");
    if (navBrand) {
      navBrand.addEventListener("click", function (e) {
        e.preventDefault();
        if (searchInput) {
          searchInput.value = "";
        }
        APP.backToList();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
