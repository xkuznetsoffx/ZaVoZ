// Вопросы опроса
const questions = [
    {
        id: 'cooking_time',
        text: 'Время готовки',
        answers: ['Быстро', 'Средне', 'Долго'],
        useDropdown: false
    },
    {
        id: 'meal_type',
        text: 'Прием пищи',
        answers: ['Завтрак', 'Обед', 'Ужин'],
        useDropdown: false
    },
    {
        id: 'difficulty',
        text: 'Сложность приготовления',
        answers: ['Легко', 'Средне', 'Тяжело'],
        useDropdown: false
    },
    {
        id: 'preference',
        text: 'Хочу приготовить',
        answers: ['Новое', 'Популярное', 'Любимое'],
        useDropdown: false
    }
];

let currentQuestionIndex = 0;
let userAnswers = {};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const nextBtn = document.getElementById('next-btn');
    const backToMainBtn = document.getElementById('back-to-main-btn');

    generateBtn.addEventListener('click', startQuiz);
    nextBtn.addEventListener('click', handleNext);
    backToMainBtn.addEventListener('click', () => {
        showScreen('main-screen');
        currentQuestionIndex = 0;
        userAnswers = {};
    });
});

function startQuiz() {
    currentQuestionIndex = 0;
    userAnswers = {};
    showScreen('quiz-screen');
    showQuestion();
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function showQuestion() {
    const question = questions[currentQuestionIndex];
    const questionText = document.getElementById('question-text');
    const answersContainer = document.getElementById('answers-container');
    const nextBtn = document.getElementById('next-btn');
    const progressFill = document.getElementById('progress-fill');

    // Обновляем прогресс
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
    progressFill.style.width = progress + '%';

    // Устанавливаем текст вопроса
    questionText.textContent = question.text;

    // Очищаем контейнер ответов
    answersContainer.innerHTML = '';

    // Скрываем кнопку "Далее"
    nextBtn.style.display = 'none';

    // Создаем кнопки ответов
    if (question.useDropdown) {
        createDropdown(question, answersContainer);
    } else {
        question.answers.forEach((answer, index) => {
            const button = document.createElement('button');
            button.className = 'answer-button';
            button.textContent = answer;
            button.addEventListener('click', () => selectAnswer(answer, button));
            answersContainer.appendChild(button);
        });
    }
}

function createDropdown(question, container) {
    const dropdownWrapper = document.createElement('div');
    dropdownWrapper.style.position = 'relative';
    dropdownWrapper.style.width = '100%';

    const dropdownButton = document.createElement('button');
    dropdownButton.className = 'dropdown-button';
    dropdownButton.textContent = 'Выберите ответ';
    dropdownButton.id = 'dropdown-button';

    const dropdownMenu = document.createElement('div');
    dropdownMenu.className = 'dropdown-menu';
    dropdownMenu.id = 'dropdown-menu';

    question.answers.forEach(answer => {
        const item = document.createElement('div');
        item.className = 'dropdown-item';
        item.textContent = answer;
        item.addEventListener('click', () => {
            selectDropdownAnswer(answer, dropdownButton);
            dropdownMenu.classList.remove('show');
            dropdownButton.classList.remove('open');
        });
        dropdownMenu.appendChild(item);
    });

    dropdownButton.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle('show');
        dropdownButton.classList.toggle('open');
    });

    // Закрываем при клике вне
    document.addEventListener('click', (e) => {
        if (!dropdownWrapper.contains(e.target)) {
            dropdownMenu.classList.remove('show');
            dropdownButton.classList.remove('open');
        }
    });

    dropdownWrapper.appendChild(dropdownButton);
    dropdownWrapper.appendChild(dropdownMenu);
    container.appendChild(dropdownWrapper);
}

function selectAnswer(answer, button) {
    // Убираем выделение с других кнопок
    document.querySelectorAll('.answer-button').forEach(btn => {
        btn.classList.remove('selected');
    });

    // Выделяем выбранную кнопку
    button.classList.add('selected');

    // Сохраняем ответ
    userAnswers[questions[currentQuestionIndex].id] = answer;

    // Показываем кнопку "Далее"
    document.getElementById('next-btn').style.display = 'block';
}

function selectDropdownAnswer(answer, button) {
    button.textContent = answer;
    userAnswers[questions[currentQuestionIndex].id] = answer;
    document.getElementById('next-btn').style.display = 'block';
}

function handleNext() {
    // Проверяем, что ответ выбран
    if (!userAnswers[questions[currentQuestionIndex].id]) {
        return;
    }

    currentQuestionIndex++;

    if (currentQuestionIndex < questions.length) {
        showQuestion();
    } else {
        // Все вопросы отвечены, отправляем на сервер
        generateRecipe();
    }
}

async function generateRecipe() {
    try {
        const response = await fetch('/api/generate-recipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userAnswers)
        });

        if (!response.ok) {
            throw new Error('Ошибка при генерации рецепта');
        }

        const recipe = await response.json();
        showRecipe(recipe);
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Произошла ошибка при генерации рецепта. Попробуйте еще раз.');
    }
}

function showRecipe(recipe) {
    const recipeContainer = document.getElementById('recipe-container');
    
    let html = `
        <h2 class="recipe-title">${recipe.recipe_name || 'Рецепт'}</h2>
        <div class="recipe-info">
    `;

    if (recipe.cooking_time) {
        html += `<div class="recipe-info-item"><strong>Время:</strong> ${recipe.cooking_time}</div>`;
    }

    if (recipe.number_of_servings) {
        html += `<div class="recipe-info-item"><strong>Порций:</strong> ${recipe.number_of_servings}</div>`;
    }

    html += `</div>`;

    if (recipe.description) {
        html += `<div class="recipe-description">${recipe.description}</div>`;
    }

    if (recipe.ingredients && recipe.ingredients.length > 0) {
        html += `
            <div class="recipe-ingredients">
                <h3>Ингредиенты:</h3>
                <ul class="ingredient-list">
        `;
        
        recipe.ingredients.forEach(ingredient => {
            const quantity = ingredient.quantity || '';
            const unit = ingredient.unit || '';
            const name = ingredient.ingredient_name || '';
            html += `<li>${quantity} ${unit} ${name}</li>`;
        });

        html += `
                </ul>
            </div>
        `;
    }

    recipeContainer.innerHTML = html;
    showScreen('result-screen');
}

