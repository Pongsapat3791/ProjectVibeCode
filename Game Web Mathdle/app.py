# app.py
# A single-file Mathdle game implementation using Flask and Object-Oriented Programming.
# This version includes difficulty levels, robust session management, and flexible equation validation.

import random
import re
from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for

# -----------------------------------------------------------------------------
# 1. Game Logic (OOP Approach)
# -----------------------------------------------------------------------------

class MathdleGame:
    """
    Encapsulates the core logic for the Mathdle game.
    This class is responsible for generating valid mathematical equations
    and checking user guesses against the correct solution.
    It does not hold any state itself, making it reusable.
    """
    def __init__(self):
        """
        Initializes the game logic constants.
        """
        self.operators = ['+', '-', '*', '/']
        self.digits = '0123456789'
        # Define difficulty levels with their corresponding equation lengths.
        self.difficulty_levels = {
            'easy': 6,
            'medium': 8,
            'hard': 10
        }

    def generate_equation(self, length):
        """
        Generates a random, valid mathematical equation of a specific length.
        The equation can be in the format 'A+B=C' or 'C=A+B'.
        """
        attempts = 0
        while attempts < 5000: # Add a safeguard to prevent infinite loops
            attempts += 1
            try:
                op = random.choice(self.operators)
                
                max_num = 10 ** (length // 2) - 1

                if op in ['+', '-']:
                    num1 = random.randint(1, max_num)
                    num2 = random.randint(1, num1)
                elif op == '*':
                    num1 = random.randint(1, int(max_num**0.5))
                    num2 = random.randint(1, int(max_num**0.5))
                elif op == '/':
                    divisor = random.randint(1, int(max_num**0.5))
                    result_val = random.randint(1, int(max_num**0.5))
                    num1 = divisor * result_val
                    num2 = divisor

                if op == '+': result = num1 + num2
                elif op == '-': result = num1 - num2
                elif op == '*': result = num1 * num2
                else: result = num1 // num2

                # Randomly decide the equation format
                if random.random() < 0.5:
                    equation = f"{num1}{op}{num2}={result}"
                else:
                    equation = f"{result}={num1}{op}{num2}"

                if len(equation) == length and self._is_valid(equation):
                    print(f"Generated Solution (len={length}): {equation}")
                    return equation
            except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
                continue
        
        print(f"Warning: Could not generate an equation of length {length}. Falling back.")
        if length == 6: return '10+5=15'
        if length == 8: return '25*4=100'
        if length == 10: return '100/10=10'
        return '1+1=2'

    def _is_valid(self, equation_str):
        """
        A helper function to validate an equation string.
        It now supports formats like 'A+B=C' and 'C=A+B'.
        """
        if equation_str.count('=') != 1:
            return False
        
        left, right = equation_str.split('=')
        if not left or not right:
            return False

        all_numbers = re.findall(r'\d+', equation_str)
        for num in all_numbers:
            if len(num) > 1 and num.startswith('0'):
                return False

        try:
            left_val = self._safe_eval(left)
            right_val_int = int(right)
            if left_val is not None and left_val == right_val_int:
                return True
        except (ValueError, TypeError):
            pass

        try:
            right_val = self._safe_eval(right)
            left_val_int = int(left)
            if right_val is not None and right_val == left_val_int:
                return True
        except (ValueError, TypeError):
            pass
        
        return False

    def _safe_eval(self, expr_str):
        """
        Safely evaluates a simple mathematical expression string.
        """
        if not all(c in self.digits + ''.join(self.operators) for c in expr_str):
            return None
        try:
            # Using eval() is safe here because we've restricted the character set.
            return eval(expr_str)
        except (SyntaxError, ZeroDivisionError, NameError, TypeError):
            return None

    def check_guess(self, guess, solution):
        """
        Compares a user's guess against the solution.
        """
        length = len(solution)
        results = [''] * length
        solution_counts = {}
        
        for i in range(length):
            char = solution[i]
            solution_counts[char] = solution_counts.get(char, 0) + 1
            if guess[i] == solution[i]:
                results[i] = 'correct'
                solution_counts[char] -= 1

        for i in range(length):
            if results[i] == 'correct':
                continue
            char = guess[i]
            if solution_counts.get(char, 0) > 0:
                results[i] = 'present'
                solution_counts[char] -= 1
            else:
                results[i] = 'absent'
        
        return results

# -----------------------------------------------------------------------------
# 2. Flask Web Application
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = 'a-very-secure-and-unique-secret-key'
mathdle_game = MathdleGame()

# --- HTML Templates ---

MENU_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale-1.0">
    <title>Mathdle - เลือกระดับความยาก</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center justify-center min-h-screen p-4">
    <div class="text-center">
        <h1 class="text-5xl font-bold tracking-wider mb-4">MATHDLE</h1>
        <p class="text-xl text-gray-400 mb-12">เกมทายสมการคณิตศาสตร์</p>
        <h2 class="text-2xl font-semibold mb-6">เลือกระดับความยาก</h2>
        <div class="flex flex-col space-y-4 w-64">
            <a href="/start?difficulty=easy" class="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg text-xl transition duration-300">ง่าย (6 ตัวอักษร)</a>
            <a href="/start?difficulty=medium" class="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-3 px-4 rounded-lg text-xl transition duration-300">ปานกลาง (8 ตัวอักษร)</a>
            <a href="/start?difficulty=hard" class="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-lg text-xl transition duration-300">ยาก (10 ตัวอักษร)</a>
        </div>
    </div>
</body>
</html>
"""

GAME_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mathdle Game</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; }
        .tile {
            width: 50px; height: 50px;
            border: 2px solid #3a3a3c;
            font-size: 1.8rem; font-weight: bold;
            display: inline-flex; align-items: center; justify-content: center;
            transition: transform 0.2s, background-color 0.5s, border-color 0.5s;
        }
        @media (min-width: 640px) { .tile { width: 60px; height: 60px; font-size: 2rem; } }
        .tile.filled { border-color: #565758; }
        .tile.correct { background-color: #538d4e; border-color: #538d4e; color: white; }
        .tile.present { background-color: #b59f3b; border-color: #b59f3b; color: white; }
        .tile.absent { background-color: #3a3a3c; border-color: #3a3a3c; color: white; }
        .tile.pop { animation: pop 0.1s ease-out; }
        @keyframes pop { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
        
        .keyboard-btn {
            height: 50px; border-radius: 4px; cursor: pointer; font-weight: bold;
            background-color: #818384; color: white;
            display: flex; justify-content: center; align-items: center;
            flex: 1; margin: 2px; user-select: none;
        }
        @media (min-width: 640px) { .keyboard-btn { height: 58px; margin: 3px; } }
        .keyboard-btn.wide { flex: 1.5; }
        .keyboard-btn.correct { background-color: #538d4e; }
        .keyboard-btn.present { background-color: #b59f3b; }
        .keyboard-btn.absent { background-color: #3a3a3c; }
    </style>
</head>
<body class="bg-gray-900 text-white">
    <div class="flex flex-col items-center justify-between min-h-screen p-2 sm:p-4">
        <header class="text-center border-b border-gray-600 pb-4 w-full max-w-md">
            <h1 class="text-4xl font-bold tracking-wider">MATHDLE</h1>
            <p class="text-gray-400">ทายสมการคณิตศาสตร์ {{ length }} ตัวอักษร</p>
        </header>

        <main id="game-container" class="flex-grow flex items-center justify-center">
            <div id="board" class="grid grid-rows-6 gap-2 my-4">
                <!-- Game board tiles will be generated by JavaScript -->
            </div>
        </main>
        
        <div id="message-popup" class="fixed top-16 left-1/2 -translate-x-1/2 bg-gray-100 text-gray-900 px-6 py-3 rounded-md shadow-lg font-semibold text-lg opacity-0 transition-opacity duration-300 z-10"></div>

        <div id="game-over-controls" class="w-full max-w-lg flex justify-center items-center space-x-4 mb-4"></div>
        
        <div id="keyboard" class="w-full max-w-lg"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const BOARD_ROWS = 6;
            const EQUATION_LENGTH = {{ length }};
            const DIFFICULTY = '{{ difficulty }}';
            const board = document.getElementById('board');
            const keyboardContainer = document.getElementById('keyboard');
            const messagePopup = document.getElementById('message-popup');

            let currentRow = 0;
            let currentCol = 0;
            let currentGuess = '';
            let isGameOver = false;

            const keyboardLayout = ['1','2','3','4','5','6','7','8','9','0','+','-','*','/','=','ENTER','BACKSPACE'];
            
            function initialize() {
                for (let i = 0; i < BOARD_ROWS; i++) {
                    const rowEl = document.createElement('div');
                    rowEl.className = `grid grid-cols-${EQUATION_LENGTH} gap-2`;
                    for (let j = 0; j < EQUATION_LENGTH; j++) {
                        const tile = document.createElement('div');
                        tile.className = 'tile';
                        tile.id = `tile-${i}-${j}`;
                        rowEl.appendChild(tile);
                    }
                    board.appendChild(rowEl);
                }

                const keyRows = [
                    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                    ['+', '-', '*', '/', '='],
                    ['ENTER', 'BACKSPACE']
                ];
                keyRows.forEach(row => {
                    const rowEl = document.createElement('div');
                    rowEl.className = 'flex w-full justify-center';
                    row.forEach(key => {
                        const btn = document.createElement('button');
                        btn.className = 'keyboard-btn';
                        if (key.length > 1) btn.classList.add('wide');
                        btn.textContent = key;
                        btn.dataset.key = key;
                        rowEl.appendChild(btn);
                    });
                    keyboardContainer.appendChild(rowEl);
                });
            }

            function handleKeyPress(key) {
                if (isGameOver) return;
                if (key === 'ENTER') submitGuess();
                else if (key === 'BACKSPACE') deleteChar();
                else if (currentCol < EQUATION_LENGTH && keyboardLayout.includes(key)) addChar(key);
            }
            
            keyboardContainer.addEventListener('click', (e) => e.target.matches('[data-key]') && handleKeyPress(e.target.dataset.key));
            document.addEventListener('keydown', (e) => {
                let key = e.key === 'Enter' ? 'ENTER' : e.key === 'Backspace' ? 'BACKSPACE' : e.key;
                handleKeyPress(key);
            });

            function addChar(char) {
                const tile = document.getElementById(`tile-${currentRow}-${currentCol}`);
                tile.textContent = char;
                tile.classList.add('filled', 'pop');
                currentGuess += char;
                currentCol++;
            }

            function deleteChar() {
                if (currentCol > 0) {
                    currentCol--;
                    currentGuess = currentGuess.slice(0, -1);
                    const tile = document.getElementById(`tile-${currentRow}-${currentCol}`);
                    tile.textContent = '';
                    tile.classList.remove('filled');
                }
            }

            async function submitGuess() {
                if (currentGuess.length !== EQUATION_LENGTH) {
                    return showMessage(`ต้องมี ${EQUATION_LENGTH} ตัวอักษร`);
                }
                try {
                    const response = await fetch('/guess', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ guess: currentGuess })
                    });
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'เกิดข้อผิดพลาด');
                    }
                    const data = await response.json();
                    updateUI(data);
                } catch (error) {
                    showMessage(error.message);
                }
            }
            
            function updateUI(data) {
                for (let i = 0; i < EQUATION_LENGTH; i++) {
                    document.getElementById(`tile-${currentRow}-${i}`).classList.add(data.results[i]);
                    const keyBtn = keyboardContainer.querySelector(`[data-key="${currentGuess[i]}"]`);
                    const status = data.results[i];
                    const currentStatus = keyBtn.classList.contains('correct') ? 'correct' : keyBtn.classList.contains('present') ? 'present' : 'absent';
                    if (status === 'correct' || (status === 'present' && currentStatus !== 'correct')) {
                         keyBtn.classList.remove('present', 'absent');
                         keyBtn.classList.add(status);
                    } else if (status === 'absent' && !keyBtn.classList.contains('correct') && !keyBtn.classList.contains('present')) {
                        keyBtn.classList.add('absent');
                    }
                }

                if (data.is_correct) {
                    isGameOver = true;
                    showMessage('ยอดเยี่ยม! คุณชนะ!', 3000);
                    createGameOverButtons();
                } else {
                    currentRow++;
                    currentCol = 0;
                    currentGuess = '';
                    if (currentRow === BOARD_ROWS) {
                        isGameOver = true;
                        showMessage(`คุณแพ้! เฉลย: ${data.solution}`, 5000);
                        createGameOverButtons();
                    }
                }
            }

            function showMessage(msg, duration = 1500) {
                messagePopup.textContent = msg;
                messagePopup.classList.add('opacity-100');
                setTimeout(() => messagePopup.classList.remove('opacity-100'), duration);
            }

            function createGameOverButtons() {
                const buttonContainer = document.getElementById('game-over-controls');
                if (buttonContainer.hasChildNodes()) return;

                const playAgainBtn = document.createElement('a');
                playAgainBtn.textContent = 'เล่นอีกครั้ง';
                playAgainBtn.href = `/start?difficulty=${DIFFICULTY}`;
                playAgainBtn.className = 'px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-bold text-lg';

                const lobbyBtn = document.createElement('a');
                lobbyBtn.textContent = 'เลือกความยากใหม่';
                lobbyBtn.href = '/';
                lobbyBtn.className = 'px-6 py-3 bg-gray-600 hover:bg-gray-700 rounded-lg text-white font-bold text-lg';
                
                buttonContainer.appendChild(playAgainBtn);
                buttonContainer.appendChild(lobbyBtn);
            }

            initialize();
        });
    </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# 3. Flask Routes (API Endpoints)
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """
    Displays the difficulty selection menu.
    """
    return render_template_string(MENU_TEMPLATE)

@app.route('/start')
def start_game():
    """
    Starts a new game.
    """
    difficulty = request.args.get('difficulty', 'medium')
    if difficulty not in mathdle_game.difficulty_levels:
        difficulty = 'medium'

    session.clear()
    session['difficulty'] = difficulty
    length = mathdle_game.difficulty_levels[difficulty]
    session['length'] = length
    session['solution'] = mathdle_game.generate_equation(length)
    session['guesses'] = []
    
    return redirect(url_for('play'))

@app.route('/play')
def play():
    """
    Renders the main game board.
    """
    if 'solution' not in session:
        return redirect(url_for('index'))
    
    length = session['length']
    difficulty = session.get('difficulty', 'medium')
    return render_template_string(GAME_TEMPLATE, length=length, difficulty=difficulty)

@app.route('/guess', methods=['POST'])
def process_guess():
    """
    Handles the user's guess submission.
    """
    if 'solution' not in session:
        return jsonify({'error': 'ไม่มีเกมในระบบ'}), 400

    data = request.get_json()
    guess = data.get('guess')
    solution = session['solution']
    length = session['length']

    if not guess or len(guess) != length:
        return jsonify({'error': f'ต้องมี {length} ตัวอักษร'}), 400

    # RE-ENABLING the check for a mathematically valid guess.
    if not mathdle_game._is_valid(guess):
        return jsonify({'error': 'สมการไม่ถูกต้อง'}), 400

    results = mathdle_game.check_guess(guess, solution)
    is_correct = all(r == 'correct' for r in results)
    
    session['guesses'].append({'guess': guess, 'results': results})
    session.modified = True

    return jsonify({
        'results': results,
        'is_correct': is_correct,
        'solution': solution if is_correct or len(session['guesses']) >= 6 else None
    })

# -----------------------------------------------------------------------------
# 4. Main Execution Block
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True, port=5002)

