(function () {
  "use strict";

  var APP = window.__quro_notebook__ || {};
  window.__quro_notebook__ = APP;

  var bm25Index = null;
  var embeddingsData = null;
  var bgeExtractor = null;
  var bgeLoading = false;
  var bgeLoaded = false;

  var QURO_SEARCH_URL = null;

  function loadConfig() {
    return fetch("data/config.json")
      .then(function (resp) {
        if (!resp.ok) throw new Error("no config");
        return resp.json();
      })
      .then(function (cfg) {
        QURO_SEARCH_URL = cfg.quro_search_url || null;
      })
      .catch(function () {});
  }

  function buildBm25Index(pages) {
    bm25Index = null;
    if (!window.MiniSearch) return;

    bm25Index = new MiniSearch({
      fields: ["title", "tags", "summary"],
      storeFields: ["doc_id", "title", "tags"],
      searchOptions: {
        boost: { title: 2 },
        fuzzy: 0.2,
      },
    });

    var docs = pages.map(function (p) {
      return {
        id: p.doc_id,
        doc_id: p.doc_id,
        title: p.title || p.doc_id,
        tags: (p.tags || []).join(" "),
        summary: p.summary || "",
      };
    });

    bm25Index.addAll(docs);
  }

  function loadEmbeddings() {
    fetch("data/embeddings.json")
      .then(function (resp) {
        if (!resp.ok) throw new Error("embeddings not available");
        return resp.json();
      })
      .then(function (data) {
        embeddingsData = data;
        initBge();
      })
      .catch(function () {
        embeddingsData = null;
      });
  }

  function initBge() {
    if (bgeLoading || bgeLoaded) return;

    if (!window.__quro_transformer_pipeline) {
      import("__TRANSFORMERS_URL__")
        .then(function (m) {
          window.__quro_transformer_pipeline = m.pipeline;
          loadBgeModel();
        })
        .catch(function () {
          bgeLoading = false;
        });
      bgeLoading = true;
      return;
    }

    loadBgeModel();
  }

  function loadBgeModel() {
    var pipeline = window.__quro_transformer_pipeline;
    if (!pipeline) {
      bgeLoading = false;
      return;
    }

    bgeLoading = true;
    pipeline("feature-extraction", "Xenova/bge-small-en-v1.5", {
      dtype: "fp32",
    })
      .then(function (extractor) {
        bgeExtractor = extractor;
        bgeLoaded = true;
        bgeLoading = false;
      })
      .catch(function () {
        bgeLoading = false;
      });
  }

  function cosineSimilarity(a, b) {
    var dot = 0;
    var normA = 0;
    var normB = 0;
    for (var i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    var denom = Math.sqrt(normA) * Math.sqrt(normB);
    return denom === 0 ? 0 : dot / denom;
  }

  function searchBm25(query) {
    if (!bm25Index) return [];
    var results = bm25Index.search(query, { prefix: true });
    return results.map(function (r) {
      return {
        doc_id: r.id,
        title: r.title || r.id,
        score: r.score,
        snippet: "",
        tags: r.tags || [],
      };
    });
  }

  function searchQuroDoc(query) {
    if (!QURO_SEARCH_URL) return Promise.resolve([]);
    return fetch(QURO_SEARCH_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_k: 10 }),
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error("quro-doc search failed");
        return resp.json();
      })
      .then(function (data) {
        var hits = Array.isArray(data) ? data : data.results || data.hits || [];
        return hits.map(function (h) {
          return {
            doc_id: h.doc_id,
            title: h.title || h.doc_id || "",
            score: h.score || 0,
            snippet: h.snippet || h.content || "",
            tags: h.tags || [],
          };
        });
      })
      .catch(function () {
        return [];
      });
  }

  function searchBgeClient(query) {
    if (!bgeLoaded || !bgeExtractor || !embeddingsData) {
      return Promise.resolve([]);
    }
    return bgeExtractor(query, { pooling: "cls", normalize: true }).then(
      function (output) {
        var qvec = Array.from(output.data);
        var scored = [];
        for (var i = 0; i < embeddingsData.docs.length; i++) {
          var d = embeddingsData.docs[i];
          var sim = cosineSimilarity(qvec, d.embedding);
          scored.push({
            doc_id: d.doc_id,
            title: d.title || d.doc_id,
            score: sim,
            snippet: "",
            tags: [],
          });
        }
        scored.sort(function (a, b) {
          return b.score - a.score;
        });
        return scored.slice(0, 10);
      }
    );
  }

  function mergeResults(bm25Results, semanticResults, bm25Weight) {
    if (!bm25Weight) bm25Weight = 0.6;
    var merged = {};
    var maxBm25 = 0;
    var maxSem = 0;
    bm25Results.forEach(function (r) {
      if (r.score > maxBm25) maxBm25 = r.score;
    });
    semanticResults.forEach(function (r) {
      if (r.score > maxSem) maxSem = r.score;
    });

    function add(docId, item, isSemantic) {
      if (!merged[docId]) {
        merged[docId] = { doc_id: docId, title: item.title, snippet: item.snippet || "", tags: item.tags || [], bm25: 0, sem: 0 };
      }
      if (isSemantic) {
        merged[docId].sem = item.score;
        if (item.snippet && !merged[docId].snippet) merged[docId].snippet = item.snippet;
      } else {
        merged[docId].bm25 = item.score;
        if (item.snippet && !merged[docId].snippet) merged[docId].snippet = item.snippet;
      }
    }

    bm25Results.forEach(function (r) {
      add(r.doc_id, r, false);
    });
    semanticResults.forEach(function (r) {
      add(r.doc_id, r, true);
    });

    var list = Object.values(merged);
    list.forEach(function (item) {
      var bm25Norm = maxBm25 > 0 ? item.bm25 / maxBm25 : 0;
      var semNorm = maxSem > 0 ? item.sem / maxSem : 0;
      item.score = bm25Weight * bm25Norm + (1 - bm25Weight) * semNorm;
    });
    list.sort(function (a, b) {
      return b.score - a.score;
    });
    return list;
  }

  APP.search = function (query) {
    var bm25Results = searchBm25(query);

    if (APP.showResults) {
      APP.showResults(bm25Results);
    }

    Promise.all([searchQuroDoc(query), searchBgeClient(query)]).then(
      function (results) {
        var quroResults = results[0];
        var bgeResults = results[1];

        var semanticResults = quroResults.length > 0 ? quroResults : bgeResults;
        if (semanticResults.length === 0) return;

        var merged = mergeResults(bm25Results, semanticResults, 0.6);
        if (APP.showResults) {
          APP.showResults(merged);
        }
      }
    );
  };

  function init() {
    function onIndexReady(pages) {
      buildBm25Index(pages);
      loadConfig().then(function () {
        loadEmbeddings();
      });
    }

    var checkInterval = setInterval(function () {
      if (APP.getState) {
        var st = APP.getState();
        if (st.pages && st.pages.length > 0) {
          clearInterval(checkInterval);
          onIndexReady(st.pages);
        }
      }
    }, 200);

    setTimeout(function () {
      clearInterval(checkInterval);
    }, 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
