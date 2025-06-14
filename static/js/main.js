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
        // Ensure placeholder exists at static/images/placeholder_bg.png
        this.load.image('placeholder_bg', '/static/images/placeholder_bg.png');
    }

    function create() {
        fetch('/api/new_game/', {
            method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({})
        })
        .then(res => {
            if (!res.ok) {
                console.error('New game HTTP error:', res.status, res.statusText);
                return res.json().then(errData => console.error('Error details:', errData)).catch(() => {});
            }
            return res.json();
        })
        .then(data => {
            if (!data) return;
            if(data.error) { console.error('New game error:', data.error); return; }
            gameId = data.game_id;
            dialogueData = data.level;
            levelSummary = data.level_summary || '';
            currentNodeId = dialogueData.start_node;
            choicePath = [];
            awaitingNext = false;
            loadAndDisplayBackground(this, dialogueData, currentNodeId, levelSummary);
        })
        .catch(err => console.error('Error starting new game (network?):', err));
    }

    function update() {}

    function loadAndDisplayBackground(scene, level, nodeId, lvlSummary) {
        const node = level.dialogue_nodes.find(n => n.id === nodeId);
        const placeholderKey = 'placeholder_bg';
        scene.load.image(placeholderKey, '/static/images/placeholder_bg.png');
        scene.load.once('complete', () => {
            if(backgroundImage) backgroundImage.destroy();
            backgroundImage = scene.add.image(400,300,placeholderKey).setDisplaySize(800,600);
            if(node && node.scene_description) {
                fetch('/api/generate_background/', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({ level_number: level.level_number, level_summary: lvlSummary, scene_description: node.scene_description })
                })
                .then(res => {
                    if (!res.ok) {
                        console.error('GenerateBackground HTTP error:', res.status, res.statusText);
                        return null;
                    }
                    return res.json();
                })
                .then(resdata => {
                    if (resdata && resdata.url) {
                        const bgKey = `bg_${resdata.image_name}`;
                        // Load the generated image URL
                        scene.load.image(bgKey, resdata.url);
                        scene.load.once('complete', () => {
                            if(backgroundImage) backgroundImage.destroy();
                            backgroundImage = scene.add.image(400,300,bgKey).setDisplaySize(800,600);
                            displayNode(scene, nodeId);
                        });
                        scene.load.start();
                    } else {
                        // Fallback to placeholder
                        displayNode(scene, nodeId);
                    }
                })
                .catch(err=>{ console.error('BG gen network error:', err); displayNode(scene, nodeId); });
            } else {
                displayNode(scene, nodeId);
            }
        });
        scene.load.start();
    }

    function displayNode(scene, nodeId) {
        if(texts.title) texts.title.destroy(); if(texts.body) texts.body.destroy();
        if(texts.choices) texts.choices.forEach(t=>t.destroy()); if(texts.choiceIndicator) texts.choiceIndicator.destroy(); if(texts.bgGraphics) texts.bgGraphics.destroy();
        const node = dialogueData.dialogue_nodes.find(n=>n.id===nodeId);
        if(!node) { console.error('Node not found:', nodeId); return; }
        const graphics = scene.add.graphics(); graphics.fillStyle(0x000000,0.8); graphics.fillRect(50,400,700,170); texts.bgGraphics=graphics;
        texts.title = scene.add.text(60,410,`${node.speaker}:`,{font:'16px Courier',fill:'#fff'});
        texts.body = scene.add.text(60,435,wrapText(node.text,80),{font:'16px Courier',fill:'#fff'});
        const choices = node.choices||[]; texts.choices=[]; let selected=0;
        if(choices.length===0) {
            texts.choices.push(scene.add.text(60,520,'Press ENTER to continue...',{font:'16px Courier',fill:'#ff0'}));
            scene.input.keyboard.once('keydown-ENTER',()=>onLevelComplete(scene)); return;
        }
        choices.forEach((ch,idx)=>{ texts.choices.push(scene.add.text(80,485+idx*20,ch.text,{font:'16px Courier',fill:'#fff'})); });
        texts.choiceIndicator=scene.add.text(60,485,'>',{font:'16px Courier',fill:'#ff0'});
        function updateIndicator(){ texts.choiceIndicator.setPosition(60,485+selected*20); } updateIndicator();
        const onKeyDown = (event) => {
            if(event.key==='ArrowUp'){ selected=(selected-1+choices.length)%choices.length; updateIndicator(); }
            else if(event.key==='ArrowDown'){ selected=(selected+1)%choices.length; updateIndicator(); }
            else if(event.key==='Enter'){ const chosen=choices[selected]; choicePath.push({node_id:node.id,choice_text:chosen.text}); scene.input.keyboard.removeListener('keydown',onKeyDown); currentNodeId=chosen.next_id; loadAndDisplayBackground(scene,dialogueData,currentNodeId,levelSummary);}        };
        scene.input.keyboard.on('keydown',onKeyDown);
    }

    function onLevelComplete(scene) {
        if(awaitingNext) return; awaitingNext=true;
        fetch('/api/headline/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game_id:gameId,choices_path:choicePath})})
        .then(res=>{ if(!res.ok){ console.error('Headline HTTP error',res.status); return null;} return res.json(); })
        .then(data=>{ if(data && data.headline) displayHeadline(scene,data.headline); else if(data) console.error('Headline error:',data.error); })
        .catch(err=>console.error('Headline network error:',err));
        fetch('/api/next_level/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game_id:gameId,choices_path:choicePath})})
        .then(res=>{ if(!res.ok){ console.error('Next level HTTP error',res.status); return null;} return res.json(); })
        .then(data=>{
            if(!data) return;
            if(data.error){ console.error('Next level error:',data.error); return; }
            if(data.message){ displayCompletion(scene,data.message); return; }
            dialogueData=data.level; levelSummary=data.level_summary||''; currentNodeId=dialogueData.start_node; choicePath=[];
            setTimeout(()=>{ clearScene(scene); loadAndDisplayBackground(scene,dialogueData,currentNodeId,levelSummary); },3000);
        })
        .catch(err=>console.error('Next level network error:',err));
    }

    function displayHeadline(scene,text){ if(headlineTextObj) headlineTextObj.destroy(); const g=scene.add.graphics(); g.fillStyle(0x000000,0.7); g.fillRect(100,200,600,100); headlineTextObj=scene.add.text(120,230,wrapText(`"${text}"`,50),{font:'20px Courier',fill:'#fff'}); scene.time.delayedCall(2500,()=>{ g.destroy(); if(headlineTextObj) headlineTextObj.destroy(); }); }
    function displayCompletion(scene,msg){ clearScene(scene); const g=scene.add.graphics(); g.fillStyle(0x000000,0.8); g.fillRect(100,200,600,200); scene.add.text(150,260,msg,{font:'20px Courier',fill:'#fff'}); }
    function clearScene(scene){ scene.children.removeAll(); }
    function wrapText(text,maxChars){ const words=text.split(' '); let lines=['']; for(let w of words){ let cur=lines[lines.length-1]; if((cur+' '+w).trim().length<=maxChars) lines[lines.length-1]=(cur+' '+w).trim(); else lines.push(w);} return lines.join(''); }
});