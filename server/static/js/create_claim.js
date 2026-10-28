window.initCreateClaim = function () {
  const form = document.getElementById("claimledgerCreateForm");
  if (!form) return;

  const itemsContainer = document.getElementById("claimledgerLineItems");
  const itemTemplate = document.getElementById("claimledgerLineItemTemplate");
  const addItemButton = document.getElementById("claimledgerAddItem");
  const itemCount = document.getElementById("claimledgerItemCount");
  const itemCountLabel = document.getElementById("claimledgerItemCountLabel");
  const grandTotal = document.getElementById("claimledgerGrandTotal");

  const mainInput = document.getElementById("claimledgerMainAttachments");
  const mainList = document.getElementById("claimledgerMainAttachmentList");
  const mainSummary = document.getElementById(
    "claimledgerMainAttachmentSummary",
  );
  const mainCount = document.getElementById("claimledgerMainAttachmentCount");
  const mainSize = document.getElementById("claimledgerMainAttachmentSize");
  const mainZone = document.getElementById("claimledgerMainUploadZone");

  const startDate = document.getElementById("claimPeriodStart");
  const endDate = document.getElementById("claimPeriodEnd");

  let nextItemId = 0;
  let mainFiles = [];
  const mainPreviewUrls = new Map();

  const itemStates = new Map();

  function money(value) {
    return new Intl.NumberFormat("en-ZA", {
      style: "currency",
      currency: "ZAR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }

  function fileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function totalFileSize(files) {
    return files.reduce((total, file) => total + file.size, 0);
  }

  function formatTotalSize(bytes) {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function isImage(file) {
    return file.type.startsWith("image/");
  }

  function isPdf(file) {
    return (
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf")
    );
  }

  function getFileIcon(file) {
    const extension = file.name.split(".").pop().toLowerCase();

    if (isPdf(file)) return "bi-file-earmark-pdf";
    if (["doc", "docx"].includes(extension)) {
      return "bi-file-earmark-word";
    }
    if (["xls", "xlsx", "csv"].includes(extension)) {
      return "bi-file-earmark-excel";
    }
    if (isImage(file)) return "bi-file-earmark-image";

    return "bi-file-earmark";
  }

  function isDuplicate(files, candidate) {
    return files.some(
      (file) =>
        file.name === candidate.name &&
        file.size === candidate.size &&
        file.lastModified === candidate.lastModified,
    );
  }

  function mergeFiles(existing, incoming) {
    const merged = [...existing];

    incoming.forEach((file) => {
      if (!isDuplicate(merged, file)) {
        merged.push(file);
      }
    });

    return merged;
  }

  function syncInputFiles(input, files) {
    const transfer = new DataTransfer();

    files.forEach((file) => transfer.items.add(file));

    input.files = transfer.files;
  }

  function createPreviewUrl(file, urlMap) {
    if (!urlMap.has(file)) {
      urlMap.set(file, URL.createObjectURL(file));
    }

    return urlMap.get(file);
  }

  function revokePreviewUrl(file, urlMap) {
    const url = urlMap.get(file);

    if (url) {
      URL.revokeObjectURL(url);
      urlMap.delete(file);
    }
  }

  function clearPreviewUrls(urlMap) {
    urlMap.forEach((url) => URL.revokeObjectURL(url));
    urlMap.clear();
  }

  function renderAttachmentList({
    files,
    container,
    summary,
    countElement,
    sizeElement,
    urlMap,
    onRemove,
  }) {
    container.replaceChildren();

    const bytes = totalFileSize(files);

    summary.hidden = files.length === 0;

    countElement.textContent = `${files.length} ${files.length === 1 ? "file" : "files"} selected`;

    sizeElement.textContent = formatTotalSize(bytes);

    files.forEach((file) => {
      const card = document.createElement("div");
      card.className = "claimledger-create-attachment-card";

      const preview = document.createElement("div");
      preview.className = "claimledger-create-attachment-preview";

      if (isImage(file)) {
        const image = document.createElement("img");
        image.src = createPreviewUrl(file, urlMap);
        image.alt = `Preview of ${file.name}`;
        preview.appendChild(image);
      } else {
        const icon = document.createElement("i");
        icon.className = `bi ${getFileIcon(file)}`;
        icon.setAttribute("aria-hidden", "true");
        preview.appendChild(icon);
      }

      const info = document.createElement("div");
      info.className = "claimledger-create-attachment-info";

      const name = document.createElement("span");
      name.className = "claimledger-create-attachment-name";
      name.textContent = file.name;
      name.title = file.name;

      const meta = document.createElement("span");
      meta.className = "claimledger-create-attachment-meta";
      meta.textContent = fileSize(file.size);

      info.append(name, meta);

      const actions = document.createElement("div");
      actions.className = "claimledger-create-attachment-actions";

      if (isImage(file) || isPdf(file)) {
        const previewButton = document.createElement("button");
        previewButton.type = "button";
        previewButton.className = "claimledger-create-attachment-action";
        previewButton.innerHTML = '<i class="bi bi-eye"></i>';
        previewButton.title = "Preview file";
        previewButton.setAttribute("aria-label", `Preview ${file.name}`);

        previewButton.addEventListener("click", function () {
          const url = createPreviewUrl(file, urlMap);
          const newWindow = window.open(url, "_blank");

          if (newWindow) {
            newWindow.opener = null;
          }
        });

        actions.appendChild(previewButton);
      }

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className =
        "claimledger-create-attachment-action " +
        "claimledger-create-attachment-action--delete";
      removeButton.innerHTML = '<i class="bi bi-trash3"></i>';
      removeButton.title = "Remove attachment";
      removeButton.setAttribute("aria-label", `Remove ${file.name}`);

      removeButton.addEventListener("click", function () {
        const confirmed = window.confirm(
          `Remove "${file.name}" from this form?`,
        );

        if (!confirmed) return;

        onRemove(file);
      });

      actions.appendChild(removeButton);
      card.append(preview, info, actions);
      container.appendChild(card);
    });
  }

  // -----------------------------------------
  // MAIN CLAIM ATTACHMENTS
  // -----------------------------------------

  function renderMainAttachments() {
    syncInputFiles(mainInput, mainFiles);

    renderAttachmentList({
      files: mainFiles,
      container: mainList,
      summary: mainSummary,
      countElement: mainCount,
      sizeElement: mainSize,
      urlMap: mainPreviewUrls,

      onRemove(file) {
        mainFiles = mainFiles.filter((item) => item !== file);
        revokePreviewUrl(file, mainPreviewUrls);
        renderMainAttachments();
      },
    });
  }

  mainInput.addEventListener("change", function () {
    mainFiles = mergeFiles(mainFiles, Array.from(mainInput.files));

    renderMainAttachments();
  });

  // -----------------------------------------
  // LINE ITEM FILES
  // -----------------------------------------

  function renderItemAttachments(card, state) {
    const input = card.querySelector(".item-attachments");
    const list = card.querySelector(".item-attachment-list");
    const summary = card.querySelector(".item-attachment-summary");
    const count = card.querySelector(".item-attachment-count");
    const size = card.querySelector(".item-attachment-size");

    syncInputFiles(input, state.files);

    renderAttachmentList({
      files: state.files,
      container: list,
      summary,
      countElement: count,
      sizeElement: size,
      urlMap: state.previewUrls,

      onRemove(file) {
        state.files = state.files.filter((item) => item !== file);
        revokePreviewUrl(file, state.previewUrls);
        renderItemAttachments(card, state);
      },
    });
  }

  // -----------------------------------------
  // ITEM TOTALS
  // -----------------------------------------

  function calculateItem(card) {
    const quantityInput = card.querySelector(".item-quantity");
    const rateInput = card.querySelector(".item-rate");
    const amountDisplay = card.querySelector(".item-amount");

    const quantity = Number(quantityInput.value);
    const rate = Number(rateInput.value);

    const validQuantity =
      quantityInput.value.trim() !== "" &&
      Number.isFinite(quantity) &&
      quantity >= 0;

    const validRate =
      rateInput.value.trim() !== "" && Number.isFinite(rate) && rate >= 0;

    const amount =
      validQuantity && validRate
        ? Math.round((quantity * rate + Number.EPSILON) * 100) / 100
        : 0;

    amountDisplay.textContent = money(amount);

    return amount;
  }

  function updateTotals() {
    let total = 0;

    itemsContainer
      .querySelectorAll(".claimledger-create-line-item")
      .forEach((card) => {
        total += calculateItem(card);
      });

    total = Math.round((total + Number.EPSILON) * 100) / 100;

    grandTotal.textContent = money(total);
  }

  // -----------------------------------------
  // RENUMBER ITEMS AND INPUT NAMES
  // -----------------------------------------

  function reindexItems() {
    const cards = Array.from(
      itemsContainer.querySelectorAll(".claimledger-create-line-item"),
    );

    cards.forEach((card, index) => {
      const number = index + 1;
      const state = itemStates.get(card.dataset.itemId);

      card.querySelector(".claimledger-create-line-item-number").textContent =
        String(number).padStart(2, "0");

      card.querySelector(".claimledger-item-heading-index").textContent =
        number;

      card
        .querySelector("h3")
        .setAttribute("aria-label", `Work item ${number}`);

      card.querySelectorAll("[data-field]").forEach((input) => {
        const field = input.dataset.field;
        input.name = `line_items[${index}][${field}]`;
      });

      card.querySelector(".item-attachments").name =
        `line_items[${index}][attachments]`;

      const removeButton = card.querySelector(
        ".claimledger-create-remove-item",
      );

      removeButton.disabled = cards.length === 1;
      removeButton.title =
        cards.length === 1
          ? "At least one work item is required"
          : "Remove work item";

      removeButton.style.opacity = cards.length === 1 ? "0.45" : "1";

      if (state) {
        renderItemAttachments(card, state);
      }
    });

    itemCount.textContent = cards.length;
    itemCountLabel.textContent = cards.length === 1 ? "item" : "items";

    updateTotals();
  }

  // -----------------------------------------
  // ADD A LINE ITEM
  // -----------------------------------------

  function addItem() {
    const fragment = itemTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".claimledger-create-line-item");

    const id = String(nextItemId++);
    card.dataset.itemId = id;

    const state = {
      files: [],
      previewUrls: new Map(),
    };

    itemStates.set(id, state);
    itemsContainer.appendChild(fragment);

    const addedCard = itemsContainer.querySelector(`[data-item-id="${id}"]`);

    const fileInput = addedCard.querySelector(".item-attachments");

    // Give every work-item file input a unique ID and connect its label.
    // Without this association, clicking "Add evidence for this item"
    // may not open that item's file picker.
    fileInput.id = `claimledgerItemAttachments-${id}`;

    const fileLabel = addedCard.querySelector(
      ".claimledger-create-upload-label",
    );
    fileLabel.htmlFor = fileInput.id;

    fileInput.addEventListener("change", function () {
      state.files = mergeFiles(state.files, Array.from(fileInput.files));

      renderItemAttachments(addedCard, state);
    });

    addedCard
      .querySelector(".item-quantity")
      .addEventListener("input", updateTotals);

    addedCard
      .querySelector(".item-rate")
      .addEventListener("input", updateTotals);

    addedCard
      .querySelector(".item-unit")
      .addEventListener("change", function () {
        const customField = addedCard.querySelector(".item-custom-unit-field");

        const customInput = addedCard.querySelector(".item-custom-unit");

        const isOther = this.value === "other";

        customField.hidden = !isOther;
        customInput.disabled = !isOther;
        customInput.required = isOther;

        if (!isOther) {
          customInput.value = "";
        }
      });

    addedCard
      .querySelector(".claimledger-create-remove-item")
      .addEventListener("click", function () {
        const currentCards = itemsContainer.querySelectorAll(
          ".claimledger-create-line-item",
        );

        if (currentCards.length <= 1) return;

        const description = addedCard
          .querySelector(".item-description")
          .value.trim();

        const message = description
          ? `Remove "${description}" and all its selected evidence?`
          : "Remove this work item and all its selected evidence?";

        if (!window.confirm(message)) return;

        clearPreviewUrls(state.previewUrls);
        itemStates.delete(id);
        addedCard.remove();

        reindexItems();
      });

    reindexItems();
  }

  addItemButton.addEventListener("click", addItem);

  // -----------------------------------------
  // DRAG AND DROP UPLOAD ZONES
  // -----------------------------------------

  function setupDropZone(zone, onFiles) {
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, function (event) {
        event.preventDefault();
        zone.classList.add("is-dragging");
      });
    });

    ["dragleave", "dragend"].forEach((eventName) => {
      zone.addEventListener(eventName, function () {
        zone.classList.remove("is-dragging");
      });
    });

    zone.addEventListener("drop", function (event) {
      event.preventDefault();
      zone.classList.remove("is-dragging");

      const files = Array.from(event.dataTransfer?.files || []);

      if (files.length) {
        onFiles(files);
      }
    });
  }

  setupDropZone(mainZone, function (files) {
    mainFiles = mergeFiles(mainFiles, files);
    renderMainAttachments();
  });

  // Each item has its own upload zone.
  function setupItemDropZones() {
    itemsContainer
      .querySelectorAll(".claimledger-create-line-item")
      .forEach((card) => {
        if (card.dataset.dropZoneReady === "true") return;

        card.dataset.dropZoneReady = "true";

        const zone = card.querySelector(".claimledger-create-upload-zone");

        const id = card.dataset.itemId;
        const state = itemStates.get(id);

        setupDropZone(zone, function (files) {
          state.files = mergeFiles(state.files, files);
          renderItemAttachments(card, state);
        });
      });
  }

  const itemObserver = new MutationObserver(setupItemDropZones);

  itemObserver.observe(itemsContainer, {
    childList: true,
  });

  // -----------------------------------------
  // CLAIM PERIOD VALIDATION
  // -----------------------------------------

  function validatePeriod() {
    const start = startDate.value;
    const end = endDate.value;

    const invalid = Boolean(start && end && end < start);

    endDate.classList.toggle("is-invalid", invalid);
    endDate.setCustomValidity(
      invalid ? "The claim period end cannot be before the start date." : "",
    );

    return !invalid;
  }

  startDate.addEventListener("change", function () {
    if (startDate.value) {
      endDate.min = startDate.value;
    } else {
      endDate.removeAttribute("min");
    }

    validatePeriod();
  });

  endDate.addEventListener("change", validatePeriod);

  // -----------------------------------------
  // FORM SUBMISSION
  // -----------------------------------------

  form.addEventListener("submit", function (event) {
    const submitter = event.submitter;
    const action = submitter?.value || "submit";

    // Drafts may be incomplete.
    // The server must also permit incomplete draft data.
    if (action === "draft") {
      return;
    }

    if (!validatePeriod()) {
      event.preventDefault();
      endDate.focus();
      return;
    }

    const cards = itemsContainer.querySelectorAll(
      ".claimledger-create-line-item",
    );

    if (!cards.length) {
      event.preventDefault();
      window.alert("Add at least one work item to the claim.");
      return;
    }

    for (const card of cards) {
      const quantity = Number(card.querySelector(".item-quantity").value);

      const rate = Number(card.querySelector(".item-rate").value);

      if (
        !Number.isFinite(quantity) ||
        quantity <= 0 ||
        !Number.isFinite(rate) ||
        rate < 0
      ) {
        event.preventDefault();

        window.alert(
          "Each work item needs a quantity greater than zero " +
            "and a valid, non-negative rate.",
        );

        card
          .querySelector(
            !Number.isFinite(quantity) || quantity <= 0
              ? ".item-quantity"
              : ".item-rate",
          )
          .focus();

        return;
      }
    }
  });

  // -----------------------------------------
  // INITIALISE
  // -----------------------------------------

  addItem();
  renderMainAttachments();

  window.addEventListener("pagehide", function () {
    clearPreviewUrls(mainPreviewUrls);

    itemStates.forEach((state) => {
      clearPreviewUrls(state.previewUrls);
    });
  });
};

