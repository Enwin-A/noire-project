// static/js/main.js
window.addEventListener('load', () => {
    const config = {
        type: Phaser.AUTO,
        width: 800,
        height: 600,
        parent: 'game-container',
        pixelArt: true,
        scene: { preload, create, update }
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
    let levelSummary = '';

    function preload() {
        this.load.image('default_detective_office', '/static/images/default_detective_office.png');
        this.load.image('default_newsroom', '/static/images/default_newsroom.png');
        this.load.image('placeholder_bg', '/static/images/placeholder_bg.png');
    }

    function create() {
        fetch('/api/new_game/', {
            method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({})
        })
        .then(res => res.json())
        .then(data => {
            gameId = data.game_id;
            dialogueData = data.level;
            levelSummary = data.level_summary || '';
            currentNodeId = dialogueData.start_node;
            choicePath = [];
            awaitingNext = false;
            loadAndDisplayBackground(this, dialogueData, currentNodeId, levelSummary);
        });
    }

    function update() {}

    function loadAndDisplayBackground(scene, level, nodeId, lvlSummary) {
        const node = level.dialogue_nodes.find(n => n.id === nodeId);
        const defaultKey = level.level_number === 2 ? 'default_newsroom' : 'default_detective_office';
        if (backgroundImage) backgroundImage.destroy();
        backgroundImage = scene.add.image(400,300,defaultKey).setDisplaySize(800,600);
        if(node && node.scene_description) {
            fetch('/api/generate_background/', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ game_id: gameId, level_number: level.level_number, level_summary: lvlSummary, scene_description: node.scene_description })
            })
            .then(res => res.json())
            .then(resdata => {
                if (resdata && resdata.url) {
                    const bgKey = `bg_${resdata.image_name}`;
                    scene.load.image(bgKey, resdata.url);
                    scene.load.once('complete', () => {
                        if(backgroundImage) backgroundImage.destroy();
                        backgroundImage = scene.add.image(400,300,bgKey).setDisplaySize(800,600);
                        displayNode(scene, nodeId);
                    });
                    scene.load.start();
                } else { displayNode(scene, nodeId); }
            })
            .catch(() => displayNode(scene, nodeId));
        } else { displayNode(scene, nodeId); }
    }

    function displayNode(scene, nodeId) {
        ['title','body','choices','choiceIndicator','bgGraphics'].forEach(key => {
            if (texts[key]) {
                if (Array.isArray(texts[key])) texts[key].forEach(t=>t.destroy());
                else texts[key].destroy();
            }
        });
        const node = dialogueData.dialogue_nodes.find(n=>n.id===nodeId);
        const graphics = scene.add.graphics(); graphics.fillStyle(0x000000,0.8); graphics.fillRect(50,360,700,230); texts.bgGraphics=graphics;
        texts.title = scene.add.text(60,370,`${node.speaker}:`,{font:'14px Courier',fill:'#fff'});
        texts.body = scene.add.text(60,390,node.text,{font:'14px Courier',fill:'#fff',wordWrap:{width:680}});
        const choices = node.choices||[]; texts.choices=[]; let selected=0;
        if (choices.length===0) {
            texts.choices.push(scene.add.text(60,550,'Press ENTER to continue...',{font:'14px Courier',fill:'#ff0'}));
            scene.input.keyboard.once('keydown-ENTER',()=>onLevelComplete(scene)); return;
        }
        choices.forEach((ch,idx)=>{ texts.choices.push(scene.add.text(80,520+idx*20,ch.text,{font:'14px Courier',fill:'#fff'})); });
        texts.choiceIndicator=scene.add.text(60,520,'>',{font:'14px Courier',fill:'#ff0'});
        function updateIndicator(){ texts.choiceIndicator.setPosition(60,520+selected*20);} updateIndicator();
        const onKeyDown = event => {
            if(event.key==='ArrowUp'){ selected=(selected-1+choices.length)%choices.length;updateIndicator(); }
            else if(event.key==='ArrowDown'){ selected=(selected+1)%choices.length;updateIndicator(); }
            else if(event.key==='Enter'){
                choicePath.push({node_id:node.id,choice_text:choices[selected].text});
                scene.input.keyboard.removeListener('keydown',onKeyDown);
                currentNodeId=choices[selected].next_id;
                loadAndDisplayBackground(scene,dialogueData,currentNodeId,levelSummary);
            }
        };
        scene.input.keyboard.on('keydown',onKeyDown);
    }

    function onLevelComplete(scene) {
        if(awaitingNext) return; awaitingNext=true;
        if (choicePath.length >= 10) proceedToNextLevel(scene);
        else {
            fetch('/api/headline/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game_id:gameId,choices_path:choicePath})})
            .then(res=>res.json()).then(data=>{ if(data.headline) displayHeadline(scene,data.headline); })
            .finally(()=>proceedToNextLevel(scene));
        }
    }

    function proceedToNextLevel(scene) {
        fetch('/api/next_level/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game_id:gameId,choices_path:choicePath})})
        .then(res=>res.json()).then(data=>{
            if(data.level){ dialogueData=data.level; levelSummary=data.level_summary||''; currentNodeId=dialogueData.start_node; choicePath=[];
                setTimeout(()=>{clearScene(scene); loadAndDisplayBackground(scene,dialogueData,currentNodeId,levelSummary);},500);
            }
        });
    }

    function displayHeadline(scene,text){ if(headlineTextObj) headlineTextObj.destroy(); const g=scene.add.graphics(); g.fillStyle(0x000000,0.7); g.fillRect(100,200,600,100);
        headlineTextObj=scene.add.text(120,230,text,{font:'18px Courier',fill:'#fff',wordWrap:{width:560}});
        scene.time.delayedCall(2500,()=>{g.destroy(); headlineTextObj.destroy();});
    }

    function clearScene(scene){ scene.children.removeAll(); }
});