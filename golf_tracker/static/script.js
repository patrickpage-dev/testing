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
        const toPar = table.querySelector('[data-total-for="current-to-par"]');
        
        // Get par totals for +/- calculation
        const parOut = table.querySelector('[data-par-total="out"]');
        const parIn = table.querySelector('[data-par-total="in"]');
        const parTotal = table.querySelector('[data-par-total="total"]');

        if (!currentInputs.length) {
            return;
        }

        const updateTotals = () => {
            let outSum = 0;
            let inSum = 0;
            let outParSum = 0;
            let inParSum = 0;

            currentInputs.forEach((input) => {
                const holeNumber = Number.parseInt(input.dataset.holeNumber, 10);
                const value = Number.parseInt(input.value, 10);
                const par = Number.parseInt(input.dataset.par, 10);
                
                if (!Number.isFinite(holeNumber) || !Number.isFinite(value)) {
                    return;
                }
                
                if (holeNumber <= 9) {
                    outSum += value;
                    if (Number.isFinite(par)) {
                        outParSum += par;
                    }
                } else {
                    inSum += value;
                    if (Number.isFinite(par)) {
                        inParSum += par;
                    }
                }
            });

            const totalSum = outSum + inSum;
            const totalPar = outParSum + inParSum;
            const toParValue = totalSum - totalPar;

            if (outTotal) outTotal.textContent = outSum.toString();
            if (inTotal) inTotal.textContent = inSum.toString();
            if (total) total.textContent = totalSum.toString();
            
            if (toPar) {
                if (toParValue === 0) {
                    toPar.textContent = 'E';
                } else if (toParValue > 0) {
                    toPar.textContent = '+' + toParValue.toString();
                } else {
                    toPar.textContent = toParValue.toString();
                }
            }
        };

        currentInputs.forEach((input) => {
            input.addEventListener('input', updateTotals);
        });

        updateTotals();
    });
});