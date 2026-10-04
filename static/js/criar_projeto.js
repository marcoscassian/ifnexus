document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('project-form');
    if (!form) return;

    let currentStep = 1;
    let newImages = [];
    let newDocuments = [];
    let searchTimer;
    const imageInput = document.getElementById('imagens-input');
    const documentInput = document.getElementById('arquivos-input');
    const coverExisting = document.getElementById('cover-existing-id');
    const coverNew = document.getElementById('cover-new-index');

    const text = (selector) => (document.querySelector(selector)?.value || '').trim();
    const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase();
    const optionLabel = (selector, fallback) => {
        const select = document.querySelector(selector);
        return select?.selectedOptions[0]?.textContent || fallback;
    };
    const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
    };

    function showStep(step) {
        currentStep = Math.min(4, Math.max(1, Number(step)));
        document.querySelectorAll('.form-step').forEach(section => section.classList.toggle('active', Number(section.dataset.step) === currentStep));
        document.querySelectorAll('.stepper-item').forEach(item => {
            const number = Number(item.dataset.goStep);
            item.classList.toggle('active', number === currentStep);
            item.classList.toggle('complete', number < currentStep);
            item.setAttribute('aria-current', number === currentStep ? 'step' : 'false');
        });
        document.getElementById('previous-step').classList.toggle('hidden', currentStep === 1);
        document.getElementById('next-step').classList.toggle('hidden', currentStep === 4);
        document.getElementById('publish-project').classList.toggle('hidden', currentStep !== 4);
        if (currentStep === 4) updateReview();
        window.scrollTo({ top: Math.max(0, document.querySelector('.stepper').offsetTop - 18), behavior: 'smooth' });
    }

    function showError(name, message) {
        const error = document.querySelector(`[data-error-for="${name}"]`);
        if (error) error.textContent = message || '';
    }

    function validateStep(step) {
        let valid = true;
        const requireField = (name, message) => {
            const value = text(`[name="${name}"]`);
            showError(name, value ? '' : message);
            if (!value) valid = false;
        };
        if (step === 1) {
            requireField('titulo', 'Informe o título do projeto.');
            requireField('descricao', 'Escreva um resumo ou descrição.');
            requireField('tipo', 'Selecione um tipo de projeto.');
            requireField('curso', 'Selecione o curso.');
            const hasAuthor = !!document.querySelector('#autores-selecionados [name="autores_ids[]"]');
            showError('autores', hasAuthor ? '' : 'Adicione pelo menos um autor.');
            valid = valid && hasAuthor;
        }
        if (step === 2) {
            const objectives = [...document.querySelectorAll('[name="objetivos[]"]')].some(input => input.value.trim());
            const methods = [...document.querySelectorAll('[name="metodologias[]"]')].some(input => input.value.trim());
            showError('objetivos', objectives ? '' : 'Adicione pelo menos um objetivo.');
            showError('metodologias', methods ? '' : 'Adicione pelo menos uma etapa da metodologia.');
            valid = objectives && methods;
        }
        if (step === 3) {
            document.querySelectorAll('.client-link-error').forEach(error => error.remove());
            document.querySelectorAll('#links-list .link-row').forEach(row => {
                const input = row.querySelector('[name="links_urls[]"]');
                if (!input.value.trim()) return;
                let urlValid = false;
                try {
                    const parsed = new URL(input.value.trim());
                    urlValid = ['http:', 'https:'].includes(parsed.protocol) && !!parsed.hostname;
                } catch (_) { urlValid = false; }
                if (!urlValid) {
                    const error = document.createElement('p');
                    error.className = 'field-error client-link-error';
                    error.textContent = 'Use uma URL completa iniciada por http:// ou https://.';
                    row.insertAdjacentElement('afterend', error);
                    valid = false;
                }
            });
            const imageTypes = new Set(['jpg', 'jpeg', 'png', 'webp']);
            const invalidImage = newImages.some(file => !imageTypes.has(file.name.split('.').pop().toLowerCase()) || file.size > 8 * 1024 * 1024);
            showError('imagens', invalidImage ? 'Use imagens JPG, PNG ou WEBP de até 8 MB.' : '');
            const documentTypes = new Set(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'odt', 'odp']);
            const invalidDocument = newDocuments.some(file => !documentTypes.has(file.name.split('.').pop().toLowerCase()) || file.size > 10 * 1024 * 1024);
            showError('arquivos', invalidDocument ? 'Use documentos permitidos de até 10 MB.' : '');
            valid = valid && !invalidImage && !invalidDocument;
        }
        if (!valid) document.querySelector(`.form-step[data-step="${step}"] .field-error:not(:empty)`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return valid;
    }

    document.getElementById('next-step').addEventListener('click', () => {
        if (validateStep(currentStep)) showStep(currentStep + 1);
    });
    document.getElementById('previous-step').addEventListener('click', () => showStep(currentStep - 1));
    document.querySelectorAll('[data-go-step]').forEach(button => button.addEventListener('click', () => {
        const destination = Number(button.dataset.goStep);
        if (destination <= currentStep || validateStep(currentStep)) showStep(destination);
    }));

    document.querySelectorAll('[maxlength]').forEach(input => {
        const counter = document.querySelector(`[data-count-for="${input.id}"]`);
        const update = () => { if (counter) counter.textContent = input.value.length; updatePreview(); };
        input.addEventListener('input', update);
        update();
    });
    ['tipo', 'curso', 'status'].forEach(id => document.getElementById(id)?.addEventListener('change', updatePreview));

    function addDynamicRow(listId, name, placeholder, value = '') {
        const list = document.getElementById(listId);
        const row = document.createElement('div');
        row.className = 'dynamic-row';
        const index = document.createElement('span');
        index.className = 'row-index';
        const input = document.createElement('input');
        input.name = name;
        input.placeholder = placeholder;
        input.value = value;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'icon-button remove-row';
        remove.setAttribute('aria-label', 'Remover item');
        remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        row.append(index, input, remove);
        list.appendChild(row);
        renumberRows(list);
        input.focus();
    }
    function renumberRows(list) {
        list.querySelectorAll('.dynamic-row').forEach((row, index) => { row.querySelector('.row-index').textContent = index + 1; });
    }
    document.querySelectorAll('.add-row').forEach(button => button.addEventListener('click', () => addDynamicRow(button.dataset.target, button.dataset.name, button.dataset.placeholder)));
    form.addEventListener('click', event => {
        const remove = event.target.closest('.remove-row');
        if (!remove) return;
        const list = remove.closest('.dynamic-list');
        remove.closest('.dynamic-row').remove();
        if (!list.children.length) addDynamicRow(list.id, list.id === 'objetivos-list' ? 'objetivos[]' : 'metodologias[]', 'Descreva este item');
        renumberRows(list);
    });

    function buildSearchResult(user, onSelect) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'search-result';
        const avatar = document.createElement('span');
        avatar.className = 'avatar-initials';
        avatar.textContent = initials(user.nome);
        const copy = document.createElement('span');
        const name = document.createElement('strong');
        name.textContent = user.nome;
        const detail = document.createElement('small');
        detail.textContent = user.matricula || user.tipo_usuario || 'Usuário do IFNexus';
        copy.append(name, detail);
        button.append(avatar, copy);
        button.addEventListener('click', () => onSelect(user));
        return button;
    }

    function setupUserSearch(inputId, resultsId, onSelect, filter = '') {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultsId);
        input.addEventListener('input', () => {
            clearTimeout(searchTimer);
            const query = input.value.trim();
            if (!query) { results.classList.remove('open'); results.replaceChildren(); return; }
            searchTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/livesearch/usuarios?q=${encodeURIComponent(query)}${filter}`);
                    const users = await response.json();
                    results.replaceChildren();
                    if (!users.length) {
                        const empty = document.createElement('div');
                        empty.className = 'search-result';
                        empty.textContent = 'Nenhum usuário encontrado';
                        results.appendChild(empty);
                    } else {
                        users.forEach(user => results.appendChild(buildSearchResult(user, selected => {
                            onSelect(selected); input.value = ''; results.classList.remove('open'); results.replaceChildren();
                        })));
                    }
                    results.classList.add('open');
                } catch (_) {
                    results.replaceChildren();
                    const error = document.createElement('div');
                    error.className = 'search-result';
                    error.textContent = 'Não foi possível buscar agora.';
                    results.appendChild(error);
                    results.classList.add('open');
                }
            }, 250);
        });
    }

    function addAuthor(user) {
        const list = document.getElementById('autores-selecionados');
        if (list.querySelector(`[data-user-id="${user.id}"]`)) return;
        const row = document.createElement('div');
        row.className = 'person-chip';
        row.dataset.userId = user.id;
        const avatar = document.createElement('span'); avatar.className = 'avatar-initials'; avatar.textContent = initials(user.nome);
        const person = document.createElement('span'); person.className = 'person-name';
        const strong = document.createElement('strong'); strong.textContent = user.nome;
        const small = document.createElement('small'); small.textContent = user.matricula || 'Usuário do IFNexus';
        person.append(strong, small);
        const role = document.createElement('select'); role.name = 'autores_tipos[]'; role.setAttribute('aria-label', `Participação de ${user.nome}`);
        role.innerHTML = '<option value="principal">Autor principal</option><option value="coautor" selected>Coautor</option>';
        const id = document.createElement('input'); id.type = 'hidden'; id.name = 'autores_ids[]'; id.value = user.id;
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button remove-person'; remove.setAttribute('aria-label', `Remover ${user.nome}`); remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        row.append(avatar, person, role, id, remove);
        list.appendChild(row);
        showError('autores', '');
        updatePreview();
    }
    setupUserSearch('busca-autor', 'resultado-autores', addAuthor);
    setupUserSearch('busca-orientador', 'resultado-orientadores', user => {
        document.getElementById('orientador-id').value = user.id;
        document.querySelector('[data-advisor-name]').textContent = user.nome;
        document.getElementById('orientador-selecionado').classList.remove('hidden');
        updatePreview();
    }, '&tipo=orientador');
    form.addEventListener('click', event => {
        const remove = event.target.closest('.remove-person');
        if (remove) { remove.closest('.person-chip').remove(); updatePreview(); }
    });
    document.getElementById('remove-orientador').addEventListener('click', () => {
        document.getElementById('orientador-id').value = '';
        document.getElementById('busca-orientador').value = '';
        document.getElementById('orientador-selecionado').classList.add('hidden');
        updatePreview();
    });
    document.addEventListener('click', event => {
        if (!event.target.closest('.search-combobox')) document.querySelectorAll('.search-results').forEach(item => item.classList.remove('open'));
    });

    function addTechnology() {
        const input = document.getElementById('tecnologia-input');
        const value = input.value.trim().replace(/^,+|,+$/g, '');
        if (!value) return;
        const list = document.getElementById('tecnologias-list');
        const duplicate = [...list.querySelectorAll('input')].some(item => item.value.toLowerCase() === value.toLowerCase());
        if (duplicate) { input.value = ''; return; }
        const chip = document.createElement('span'); chip.className = 'tag-chip';
        const label = document.createElement('span'); label.textContent = value;
        const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = 'tecnologias[]'; hidden.value = value;
        const remove = document.createElement('button'); remove.type = 'button'; remove.setAttribute('aria-label', `Remover ${value}`); remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        remove.addEventListener('click', () => { chip.remove(); updatePreview(); });
        chip.append(label, hidden, remove); list.appendChild(chip); input.value = ''; updatePreview();
    }
    document.getElementById('add-tecnologia').addEventListener('click', addTechnology);
    document.getElementById('tecnologia-input').addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); addTechnology(); }
    });
    document.querySelectorAll('#tecnologias-list .tag-chip button').forEach(button => button.addEventListener('click', () => { button.closest('.tag-chip').remove(); updatePreview(); }));

    function addLink(type = 'github', url = '') {
        const row = document.createElement('div'); row.className = 'link-row';
        const select = document.createElement('select'); select.name = 'links_tipos[]';
        [['github', 'GitHub'], ['demonstracao', 'Demonstração'], ['video', 'Vídeo'], ['site', 'Site'], ['outro', 'Outro']].forEach(([value, label]) => {
            const option = document.createElement('option'); option.value = value; option.textContent = label; option.selected = value === type; select.appendChild(option);
        });
        const input = document.createElement('input'); input.type = 'url'; input.name = 'links_urls[]'; input.placeholder = 'https://'; input.value = url;
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button remove-link'; remove.setAttribute('aria-label', 'Remover link'); remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        row.append(select, input, remove); document.getElementById('links-list').appendChild(row); input.focus();
    }
    document.getElementById('add-link').addEventListener('click', () => addLink());
    form.addEventListener('click', event => { const button = event.target.closest('.remove-link'); if (button) button.closest('.link-row').remove(); });
    if (!document.querySelector('#links-list .link-row')) addLink();

    function syncFileInput(input, files) {
        const transfer = new DataTransfer();
        files.forEach(file => transfer.items.add(file));
        input.files = transfer.files;
    }
    function makeCover(card, type, value) {
        document.querySelectorAll('.image-preview').forEach(item => item.classList.remove('is-cover'));
        card.classList.add('is-cover');
        coverExisting.value = type === 'existing' ? value : '';
        coverNew.value = type === 'new' ? value : '';
        updatePreview();
    }
    function renderNewImages() {
        document.querySelectorAll('[data-new-image]').forEach(item => item.remove());
        const gallery = document.getElementById('image-gallery');
        newImages.forEach((file, index) => {
            const card = document.createElement('article'); card.className = 'image-preview'; card.dataset.newImage = index;
            const image = document.createElement('img'); image.src = URL.createObjectURL(file); image.alt = file.name;
            const label = document.createElement('span'); label.className = 'cover-label'; label.textContent = 'Capa';
            const actions = document.createElement('div'); actions.className = 'media-actions';
            const cover = document.createElement('button'); cover.type = 'button'; cover.className = 'set-cover'; cover.textContent = 'Definir como capa'; cover.addEventListener('click', () => makeCover(card, 'new', index));
            const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'remove-media'; remove.setAttribute('aria-label', 'Remover imagem'); remove.innerHTML = '<i class="fa-solid fa-trash"></i>';
            remove.addEventListener('click', () => {
                const wasCover = card.classList.contains('is-cover'); newImages.splice(index, 1); syncFileInput(imageInput, newImages); renderNewImages();
                if (wasCover) selectFirstCover();
            });
            actions.append(cover, remove); card.append(image, label, actions); gallery.appendChild(card);
            if (coverNew.value === String(index)) card.classList.add('is-cover');
        });
        if (!document.querySelector('.image-preview.is-cover')) selectFirstCover();
        updatePreview();
    }
    function selectFirstCover() {
        const first = document.querySelector('.image-preview');
        if (!first) { coverExisting.value = ''; coverNew.value = ''; updatePreview(); return; }
        if (first.dataset.existingImage) makeCover(first, 'existing', first.dataset.existingImage);
        else makeCover(first, 'new', first.dataset.newImage);
    }
    imageInput.addEventListener('change', () => {
        newImages.push(...[...imageInput.files]); syncFileInput(imageInput, newImages); renderNewImages();
    });
    document.querySelectorAll('[data-existing-image]').forEach(card => {
        card.querySelector('.set-cover').addEventListener('click', () => makeCover(card, 'existing', card.dataset.existingImage));
        card.querySelector('.remove-media').addEventListener('click', () => { const wasCover = card.classList.contains('is-cover'); card.remove(); if (wasCover) selectFirstCover(); updatePreview(); });
    });

    function renderNewDocuments() {
        document.querySelectorAll('[data-new-document]').forEach(item => item.remove());
        const list = document.getElementById('document-list');
        newDocuments.forEach((file, index) => {
            const row = document.createElement('div'); row.className = 'document-row'; row.dataset.newDocument = index;
            const extension = document.createElement('span'); extension.className = 'file-icon'; extension.textContent = file.name.split('.').pop().toUpperCase();
            const copy = document.createElement('span'); const name = document.createElement('strong'); name.textContent = file.name;
            const size = document.createElement('small'); size.textContent = `${(file.size / 1048576).toFixed(1)} MB`; copy.append(name, size);
            const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button'; remove.setAttribute('aria-label', 'Remover arquivo'); remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            remove.addEventListener('click', () => { newDocuments.splice(index, 1); syncFileInput(documentInput, newDocuments); renderNewDocuments(); });
            row.append(extension, copy, remove); list.appendChild(row);
        });
    }
    documentInput.addEventListener('change', () => { newDocuments.push(...[...documentInput.files]); syncFileInput(documentInput, newDocuments); renderNewDocuments(); });
    document.querySelectorAll('.remove-document').forEach(button => button.addEventListener('click', () => button.closest('.document-row').remove()));

    function setupDropzone(zoneId, input, collection, render) {
        const zone = document.getElementById(zoneId);
        ['dragenter', 'dragover'].forEach(type => zone.addEventListener(type, event => { event.preventDefault(); zone.classList.add('dragging'); }));
        ['dragleave', 'drop'].forEach(type => zone.addEventListener(type, event => { event.preventDefault(); zone.classList.remove('dragging'); }));
        zone.addEventListener('drop', event => { collection.push(...[...event.dataTransfer.files]); syncFileInput(input, collection); render(); });
    }
    setupDropzone('image-dropzone', imageInput, newImages, renderNewImages);
    setupDropzone('document-dropzone', documentInput, newDocuments, renderNewDocuments);

    function currentCoverSource() {
        const cover = document.querySelector('.image-preview.is-cover img');
        return cover?.src || '';
    }
    function renderCover(containerSelector) {
        const container = document.querySelector(containerSelector);
        const source = currentCoverSource();
        container.replaceChildren();
        if (source) { const image = document.createElement('img'); image.src = source; image.alt = 'Capa do projeto'; container.appendChild(image); }
        else { const icon = document.createElement('i'); icon.className = 'fa-regular fa-image'; container.appendChild(icon); }
    }
    function updatePreview() {
        setText('#preview-title', text('#titulo') || 'Título do projeto');
        setText('#preview-subtitle', text('#subtitulo') || 'Subtítulo do projeto');
        setText('#preview-description', text('#descricao') || 'O resumo do seu projeto aparecerá aqui.');
        setText('#preview-type', optionLabel('#tipo', 'Tipo do projeto'));
        setText('#preview-status', optionLabel('#status', 'Ideia'));
        const authors = document.getElementById('preview-authors'); authors.replaceChildren();
        document.querySelectorAll('#autores-selecionados .person-chip').forEach(row => {
            const avatar = document.createElement('span'); avatar.className = 'avatar-initials'; avatar.textContent = row.querySelector('.avatar-initials').textContent; avatar.title = row.querySelector('.person-name strong').textContent; authors.appendChild(avatar);
        });
        renderCover('#preview-cover');
    }
    form.addEventListener('input', event => { if (!event.target.matches('#tecnologia-input')) updatePreview(); });
    form.addEventListener('change', updatePreview);

    function fillList(selector, values, emptyText) {
        const list = document.querySelector(selector); list.replaceChildren();
        const clean = values.map(value => value.trim()).filter(Boolean);
        if (!clean.length) { const item = document.createElement('li'); item.textContent = emptyText; list.appendChild(item); return; }
        clean.forEach(value => { const item = document.createElement('li'); item.textContent = value; list.appendChild(item); });
    }
    function updateReview() {
        setText('#review-title', text('#titulo') || 'Título do projeto');
        setText('#review-subtitle', text('#subtitulo') || 'Sem subtítulo');
        setText('#review-type', optionLabel('#tipo', 'Tipo do projeto'));
        setText('#review-status', optionLabel('#status', 'Status'));
        setText('#review-description', text('#descricao') || 'Nenhum resumo informado.');
        setText('#review-results', text('#resultados') || 'Nenhum resultado informado.');
        fillList('#review-objectives', [...document.querySelectorAll('[name="objetivos[]"]')].map(item => item.value), 'Nenhum objetivo informado.');
        fillList('#review-methods', [...document.querySelectorAll('[name="metodologias[]"]')].map(item => item.value), 'Nenhuma metodologia informada.');
        const authors = [...document.querySelectorAll('#autores-selecionados .person-chip')].map(row => `${row.querySelector('.person-name strong').textContent} · ${row.querySelector('select').selectedOptions[0].textContent}`);
        const advisor = document.getElementById('orientador-selecionado').classList.contains('hidden') ? '' : document.querySelector('[data-advisor-name]').textContent;
        setText('#review-authors', authors.length ? `${authors.join(', ')}${advisor ? ` · Orientação: ${advisor}` : ''}` : 'Nenhum autor informado.');
        const tags = document.getElementById('review-tags'); tags.replaceChildren();
        document.querySelectorAll('#tecnologias-list input').forEach(input => { const chip = document.createElement('span'); chip.className = 'tag-chip'; chip.textContent = input.value; tags.appendChild(chip); });
        const imageCount = document.querySelectorAll('.image-preview').length;
        const documentCount = document.querySelectorAll('.document-row').length;
        const linkCount = [...document.querySelectorAll('[name="links_urls[]"]')].filter(input => input.value.trim()).length;
        setText('#review-materials', `${imageCount} imagem(ns), ${documentCount} documento(s) e ${linkCount} link(s).`);
        renderCover('#review-cover');
    }

    form.addEventListener('submit', event => {
        const action = event.submitter?.value;
        if (action === 'publish') {
            for (let step = 1; step <= 3; step += 1) {
                if (!validateStep(step)) { event.preventDefault(); showStep(step); return; }
            }
        }
        form.classList.add('is-submitting');
        form.querySelectorAll('button[type="submit"]').forEach(button => { if (button !== event.submitter) button.disabled = true; });
    });

    const firstServerError = document.querySelector('.field-error:not(:empty)');
    updatePreview();
    if (firstServerError) showStep(Number(firstServerError.dataset.step || 1));
    else showStep(1);
});
