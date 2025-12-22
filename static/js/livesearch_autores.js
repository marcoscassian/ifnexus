// liveserach autores

const buscaAutor = document.getElementById("busca-autor");
const resultadoAutores = document.getElementById("resultado-autores");
const autoresSelecionados = document.getElementById("autores-selecionados");

let timeoutAutor;

buscaAutor.addEventListener("input", () => {
    clearTimeout(timeoutAutor);

    timeoutAutor = setTimeout(async () => {
        const termo = buscaAutor.value.trim();

        if (!termo) {
            resultadoAutores.innerHTML = "";
            resultadoAutores.classList.remove("ativo");
            return;
        }

        const res = await fetch(`/livesearch/usuarios?q=${termo}`);
        const usuarios = await res.json();

        resultadoAutores.innerHTML = "";

        if (usuarios.length === 0) {
            resultadoAutores.innerHTML = `
                <div class="user-item">
                    <em>Nenhum usuário encontrado</em>
                </div>
            `;
            resultadoAutores.classList.add("ativo");
            return;
        }

        usuarios.forEach(u => {
            resultadoAutores.innerHTML += `
                <div class="user-item"
                    onclick="selecionarAutor(${u.id}, '${u.nome}', '${u.matricula}')">
                    <strong>${u.nome}</strong><br>
                    <small>${u.matricula}</small>
                </div>
            `;
        });

        resultadoAutores.classList.add("ativo");

    }, 300);
});

function selecionarAutor(id, nome, matricula) {
    if (autoresSelecionados.querySelector(`input[name="autores_ids[]"][value="${id}"]`)) return;

    const div = document.createElement("div");
    div.classList.add("autor");

    div.innerHTML = `
        <strong>${nome}</strong> (${matricula})
        <input type="hidden" name="autores_ids[]" value="${id}">
        <button type="button" onclick="this.parentNode.remove()">X</button>
    `;

    autoresSelecionados.appendChild(div);

    buscaAutor.value = "";
    resultadoAutores.innerHTML = "";
    resultadoAutores.classList.remove("ativo");
}
    

document.addEventListener("click", (e) => {
    if (!e.target.closest(".autor-input-group")) {
        resultadoAutores.classList.remove("ativo");
    }
});