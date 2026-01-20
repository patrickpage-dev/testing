document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        body.classList.add(savedTheme);
    } else {
        // Default to light mode if no preference is saved
        body.classList.add('light-mode');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            if (body.classList.contains('dark-mode')) {
                body.classList.remove('dark-mode');
                body.classList.add('light-mode');
                localStorage.setItem('theme', 'light-mode');
            } else {
                body.classList.remove('light-mode'); // Remove default if present
                body.classList.add('dark-mode');
                localStorage.setItem('theme', 'dark-mode');
            }
        });
    }

    const scorecardTables = document.querySelectorAll('[data-scorecard]');
    scorecardTables.forEach((table) => {
        const currentInputs = table.querySelectorAll('input[data-score-type="current"]');
        const outTotal = table.querySelector('[data-total-for="current-out"]');
        const inTotal = table.querySelector('[data-total-for="current-in"]');
        const total = table.querySelector('[data-total-for="current-total"]');

        if (!currentInputs.length || !outTotal || !inTotal || !total) {
            return;
        }

        const updateTotals = () => {
            let outSum = 0;
            let inSum = 0;

            currentInputs.forEach((input) => {
                const holeNumber = Number.parseInt(input.dataset.holeNumber, 10);
                const value = Number.parseInt(input.value, 10);
                if (!Number.isFinite(holeNumber) || !Number.isFinite(value)) {
                    return;
                }
                if (holeNumber <= 9) {
                    outSum += value;
                } else {
                    inSum += value;
                }
            });

            outTotal.textContent = outSum.toString();
            inTotal.textContent = inSum.toString();
            total.textContent = (outSum + inSum).toString();
        };

        currentInputs.forEach((input) => {
            input.addEventListener('input', updateTotals);
        });

        updateTotals();
    });
});