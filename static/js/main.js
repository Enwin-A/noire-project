// static/js/main.js

window.addEventListener('load', () => {
    const config = {
        type: Phaser.AUTO,
        width: 800,
        height: 600,
        parent: 'game-container',
        pixelArt: true,
        scene: {
            preload: preload,
            create: create,
            update: update,
        }
    };
    const game = new Phaser.Game(config);

    let dialogueData = null;
    let currentNodeId = null;
    let choicePath = [];
    let texts = {};
    let backgroundImage = null;
    let gameId = null;
    let awaitingNext = false;
    let headlineTextObj = null;

    function preload() {
        // Load placeholder background; real backgrounds loaded dynamically per level
        this.load.image('placeholder_bg', '/static/images/placeholder_bg.png');
        // Load any UI assets if needed (e.g., dialogue box image). For now, we'll draw rectangles.
    }

    function create() {
        // Start new game
        fetch('/api/new_game/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                return;
            }
            gameId = data.game_id;
            startLevel(this, data.level);
        })
        .catch(err => console.error('Error starting new game:', err));
    }

    function update() {
        // Nothing global here; input handled via key events when displaying choices
    }

    function startLevel(scene, level) {
        dialogueData = level;
        currentNodeId = dialogueData.start_node;
        choicePath = [];
        awaitingNext = false;
        // Load background based on level.background_description or image name
        // For simplicity, try to load an image with key 'bg_levelX', else use placeholder
        const bgKey = 'bg_level_' + level.level_number;
        // If background image exists in static/images named e.g. 'level1_bg.png', load it dynamically.
        const imageName = level.background_image || `level${level.level_number}_bg.png`;
        // Dynamically load background; if fails, fallback to placeholder
        scene.load.image(bgKey, '/static/images/' + imageName);
        scene.load.once('complete', () => {
            if (backgroundImage) {
                backgroundImage.destroy();
            }
            backgroundImage = scene.add.image(400, 300, bgKey).setDisplaySize(800, 600);
            displayNode(scene, currentNodeId);
        });
        scene.load.start();
    }

    function displayNode(scene, nodeId) {
        // Clear previous text objects
        if (texts.title) texts.title.destroy();
        if (texts.body) texts.body.destroy();
        if (texts.choices) {
            texts.choices.forEach(t => t.destroy());
        }
        if (texts.choiceIndicator) texts.choiceIndicator.destroy();
        
        const node = dialogueData.dialogue_nodes.find(n => n.id === nodeId);
        if (!node) {
            console.error('Node not found:', nodeId);
            return;
        }
        // Display dialogue box (draw rectangle)
        const graphics = scene.add.graphics();
        graphics.fillStyle(0x000000, 0.8);
        graphics.fillRect(50, 400, 700, 170);
        texts.bgGraphics = graphics;

        // Display speaker and text
        texts.title = scene.add.text(60, 410, `${node.speaker}:`, { font: '16px Courier', fill: '#ffffff' });
        texts.body = scene.add.text(60, 435, wrapText(node.text, 80), { font: '16px Courier', fill: '#ffffff' });

        // Display choices
        const choices = node.choices || [];
        texts.choices = [];
        let selected = 0;
        if (choices.length === 0) {
            // Terminal node: offer to proceed to next level
            texts.choices.push(scene.add.text(60, 520, 'Press ENTER to continue...', { font: '16px Courier', fill: '#ffff00' }));
            scene.input.keyboard.once('keydown-ENTER', () => {
                onLevelComplete(scene);
            });
            return;
        }
        // Display each choice
        choices.forEach((ch, idx) => {
            const textObj = scene.add.text(80, 485 + idx * 20, ch.text, { font: '16px Courier', fill: '#ffffff' });
            texts.choices.push(textObj);
        });
        // Indicator
        texts.choiceIndicator = scene.add.text(60, 485, '>', { font: '16px Courier', fill: '#ffff00' });

        function updateIndicator() {
            const y = 485 + selected * 20;
            texts.choiceIndicator.setPosition(60, y);
        }
        updateIndicator();
        // Input handlers
        const keys = scene.input.keyboard.addKeys('UP,DOWN,ENTER');
        const onKeyDown = (event) => {
            if (event.key === 'ArrowUp') {
                selected = (selected - 1 + choices.length) % choices.length;
                updateIndicator();
            } else if (event.key === 'ArrowDown') {
                selected = (selected + 1) % choices.length;
                updateIndicator();
            } else if (event.key === 'Enter') {
                // Record choice
                const chosen = choices[selected];
                choicePath.push({ node_id: node.id, choice_text: chosen.text });
                // Clean up keys listener
                scene.input.keyboard.removeListener('keydown', onKeyDown);
                // Proceed to next node
                currentNodeId = chosen.next_id;
                displayNode(scene, currentNodeId);
            }
        };
        scene.input.keyboard.on('keydown', onKeyDown);
    }

    function onLevelComplete(scene) {
        if (awaitingNext) return;
        awaitingNext = true;
        // Display headline while generating next level
        fetch('/api/headline/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ game_id: gameId, choices_path: choicePath })
        })
        .then(res => res.json())
        .then(data => {
            if (data.headline) displayHeadline(scene, data.headline);
            else console.error('Headline error', data.error);
        })
        .catch(err => console.error('Error fetching headline:', err));
        // Generate next level
        fetch('/api/next_level/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ game_id: gameId, choices_path: choicePath })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error('Next level error', data.error);
                return;
            }
            if (data.message) {
                // Game completed
                displayCompletion(scene, data.message);
                return;
            }
            // Start next level after short delay to let user read headline
            setTimeout(() => {
                clearScene(scene);
                startLevel(scene, data.level);
            }, 3000);
        })
        .catch(err => console.error('Error generating next level:', err));
    }

    function displayHeadline(scene, text) {
        // Display a newspaper-style headline overlay
        if (headlineTextObj) headlineTextObj.destroy();
        // Semi-transparent overlay
        const graphics = scene.add.graphics();
        graphics.fillStyle(0x000000, 0.7);
        graphics.fillRect(100, 200, 600, 100);
        // Headline text
        headlineTextObj = scene.add.text(120, 230, wrapText(`"${text}"`, 50), { font: '20px Courier', fill: '#ffffff' });
        // Destroy after a few seconds
        scene.time.delayedCall(2500, () => {
            graphics.destroy();
            if (headlineTextObj) headlineTextObj.destroy();
        });
    }

    function displayCompletion(scene, message) {
        // Clear and show completion message
        clearScene(scene);
        const graphics = scene.add.graphics();
        graphics.fillStyle(0x000000, 0.8);
        graphics.fillRect(100, 200, 600, 200);
        scene.add.text(150, 260, message, { font: '20px Courier', fill: '#ffffff' });
    }

    function clearScene(scene) {
        // Destroy all children except camera etc.
        scene.children.removeAll();
    }

    // Utility: wrap text by max chars per line
    function wrapText(text, maxChars) {
        const words = text.split(' ');
        let lines = [''];
        for (let word of words) {
            let current = lines[lines.length - 1];
            if ((current + ' ' + word).trim().length <= maxChars) {
                lines[lines.length - 1] = (current + ' ' + word).trim();
            } else {
                lines.push(word);
            }
        }
        return lines.join('\n');
    }
});