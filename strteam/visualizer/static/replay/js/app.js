/**
 * Creates a coordinate object for a character with the specified properties.
 *
 * @param {string} character - The name of the character.
 * @param {string} imgid - The ID indicating which side (left/right) the character's image should be on.
 * @param {string} top - The CSS top position for the character.
 * @param {string} left - The CSS left position for the character.
 * @returns {Object} A coordinate object with the specified properties.
 */
const createCoord = (character, imgid, top, left) => ({ character, imgid, top, left });

const coordSet = {
    "Chief Executive Officer": createCoord("Chief Executive Officer", "right", "-315px", "280px"),
    "Chief Product Officer": createCoord("Chief Product Officer", "left", "-165px", "110px"),
    "Chief Human Resource Officer": createCoord("Chief Human Resource Officer", "left", "-305px", "55px"),
    "Code Reviewer": createCoord("Code Reviewer", "left", "-185px", "500px"),
    "Programmer": createCoord("Programmer", "right", "-80px", "300px"),
    "Chief Technology Officer": createCoord("Chief Technology Officer", "right", "-130px", "340px"),
    "Chief Creative Officer": createCoord("Chief Creative Officer", "right", "-95px", "205px"),
    "Software Test Engineer": createCoord("Software Test Engineer", "right", "-90px", "470px"),
    "User": createCoord("User", "left", "-465px", "125px"),
    "Counselor": createCoord("Counselor", "right", "-360px", "420px"),
    "Prompt Engineer": createCoord("Prompt Engineer", "right", "-320px", "20px"),
    "System": createCoord("System", "left", "-405px", "20px"),
    "HTTP Request": createCoord("HTTP Request", "right", "-405px", "20px")
};


const Softwareinfo = {
    "duration": "-1",
    "cost": "-1",
    "version_updates": "-1",
    "num_code_files": "-1",
    "num_png_files": "-1",
    "num_doc_files": "-1",
    "code_lines": "-1",
    "env_lines": "-1",
    "manual_lines": "-1",
    "num_utterances": "-1",
    "num_self_reflections": "-1",
    "num_prompt_tokens": "-1",
    "num_completion_tokens": "-1",
    "num_total_tokens": "-1",
};

// Configuration for character appearance speed and scrolling behavior
const config = {
    timeInterval: 5,
    charInterval: 1,
    scrollInterval: 40
};

// Variables for managing content and dialog states
let contents, filename, curDialog = '', totalHeight = 0;
let curPara = '', curCommand = '', idx = 0, dialog;
let replaying = 0, ifStop = 0, isPaused = false, pauseIntervalId;
let ifMove = true;
const md = window.markdownit();

//watch replay button clicked
const button = document.getElementById('replay');
button.addEventListener('click', () => {
    replayDialog(idx);
});

$(document).ready(function() {
    $('#filebutton').click(function() {
        $('#fileInput').click();
    });

});

const dialogbody = document.getElementById("dialogBody");
dialogbody.addEventListener("mousewheel", handleMouseWheel, false);

function handleMouseWheel(event) {
    if (event.wheelDelta > 0) {
        if_move = false;
    } else if (event.wheelDelta < 0) {
        if (dialogbody.scrollTop + dialogbody.clientHeight == dialogbody.scrollHeight) {
            if_move = true;
        }
    }
}

function getinterval(speed) {

    if (speed < 80 && speed > 40) {
        timeinterval = 250 / speed;
        charinterval = 2;
        scrollinterval = 80;
    } else if (speed <= 40 && speed > 0) {
        timeinterval = 150 / speed;
        charinterval = 1;
        scrollinterval = 80;
    } else if (speed >= 80 && speed < 90) {
        timeinterval = 100 / speed;
        charinterval = 1;
        scrollinterval = 100;
    } else if (speed >= 90 && speed <= 100) {
        timeinterval = 5 / speed;
        charinterval = 1;
        scrollinterval = 400;
    }
}
//use the slider to control the replay speed
function speedchange() {
    var speedbar = document.getElementById("speed");
    var speed = speedbar.value;
    if (speed == 0) {
        if (!isPaused) {
            isPaused = true;
            clearInterval(pauseIntervalId);
            updateCompanyWorking("end");
        }
    } else if (speed != 0 && isPaused == true) {
        getinterval(speed);
        isPaused = false;
        idx += 1;
        replayDialog(idx);
    } else if (speed != 0) {
        isPaused = false;
        getinterval(speed);
    }
}
// do replay
async function replayDialog(idx) {
    if (replaying == 1 && idx == 0) {
        return;
    }
    if (idx == 0) {
        replaying = 1;
        console.log("Attempting to replay");
        dialog = extraction(contents);
        var filelable = document.getElementById("successupload");
        filelable.style.display = "block";
        var info = "Replaying `" + filename + "` ......";
        filelable.innerHTML = md.render(info);
    }
    for (let i = idx; i < dialog.length; ++i) {
        console.log("Replaying dialog", i);
        console.log(dialog[i]);
        await createPara(dialog[i], i);
    }
}

//watch .log file input
function watchfileInput(files) {
    if (files.length) {
        const file = files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function() {
                contents = this.result;
            };
            reader.readAsText(file);
            var filelable = document.getElementById("successupload");
            filelable.style.display = "block";
            var info = "File uploaded (`" + file.name + "`). Please click **\"Replay\"** to show Startr.Team's development process";
            filename = file.name;
            filelable.innerHTML = md.render(info);
        }
    }
}

function extraction(contents) {
    console.log("Starting extraction process...");

    // First pass: collect all lines and identify potential dialog sections
    const lines = contents.split('\n');
    console.log(`Total lines in log file: ${lines.length}`);
    
    // Updated regex to capture log entries with the correct format
    const regex = /^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+)\] (.*)$/;
    
    var matches = [];
    let match;
    
    // Process each line
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        match = regex.exec(line);
        if (match) {
            const timestamp = match[1];
            const level = match[2];
            const text = match[3];
            matches.push({ timestamp, level, text, lineNum: i });
        }
    }

    console.log("Total matches found: ", matches.length);

    const dialog = [];
    let count = 0;

    // Patterns for various log components
    const regex_start = /\*\*Startr\.Team Starts\*\* \(([^)]+)\)/;
    const regex_task = /\*\*task_prompt\*\*: (.*)/;
    const regex_chat_section = /\*\*\[chatting\]\*\*/;
    const regex_assistant = /^(.+?): ([\s\S]+?)(?=\n\n\[|\n\n$|$)/m;
    const regex_user = /^(.+?): ([\s\S]+?)(?=\n\n\[|\n\n$|$)/m;
    
    // Extract session start info and task
    for (let i = 0; i < matches.length; i++) {
        const { timestamp, level, text } = matches[i];
        
        // Extract session start
        let start_match = regex_start.exec(text);
        if (start_match) {
            console.log("Matched start of session:", start_match[1]);
            dialog.push({
                start: "Startr.Team Starts",
                timestamp: start_match[1]
            });
            continue;
        }
        
        // Extract task prompt
        let task_match = regex_task.exec(text);
        if (task_match) {
            console.log("Matched task:", task_match[1]);
            dialog.push({
                task: task_match[1]
            });
            continue;
        }
        
        // Look for chat sections and extract dialogs
        if (regex_chat_section.test(text)) {
            console.log("Found chat section at line:", matches[i].lineNum);
            
            // Extract conversations by processing subsequent lines
            let j = i + 1;
            while (j < matches.length) {
                const dialogText = matches[j].text;
                
                // Try to match as assistant dialog
                let dialog_match = regex_assistant.exec(dialogText);
                if (dialog_match && dialog_match[1] && dialog_match[1].length < 50) { // Reasonable role name length
                    const role = dialog_match[1].trim();
                    const content = dialog_match[2].trim();
                    
                    // Don't add system messages
                    if (role !== 'System') {
                        console.log(`Matched dialog from ${role}`);
                        dialog.push({
                            type: role.includes("Chief") ? "assistant" : "user",
                            character: role,
                            command: content,
                            len: content.length,
                            count: ++count
                        });
                    }
                    j++;
                    continue;
                }
                
                // Move to next line if no match
                j++;
            }
            
            // Skip processed lines
            i = j - 1;
        }
    }

    // If we didn't find structured dialogs, try simpler pattern matching
    if (dialog.length <= 2) { // Just start and task
        console.log("No structured dialogs found, trying simpler pattern matching...");
        
        for (let i = 0; i < matches.length; i++) {
            const { text } = matches[i];
            
            // Look for simple dialog format with roles
            const simple_dialog = /^([\w\s]+?):\s+(.+)$/m.exec(text);
            if (simple_dialog && simple_dialog[1] && simple_dialog[1].length < 50) {
                const role = simple_dialog[1].trim();
                const content = simple_dialog[2].trim();
                
                if (role !== 'System' && content.length > 10) {
                    console.log(`Matched simple dialog from ${role}`);
                    dialog.push({
                        type: role.includes("Chief") ? "assistant" : "user",
                        character: role,
                        command: content,
                        len: content.length,
                        count: ++count
                    });
                }
            }
        }
    }

    console.log("Extraction complete. Total dialogs extracted:", dialog.length);
    return dialog;
}



//show dailog
function createPara(d, i) {
    const singleDialog = document.createElement("div");
    singleDialog.style.position = "relative";
    curdialog = singleDialog;
    singleDialog.style.display = "flex";
    singleDialog.style.flexDirection = "column";
    singleDialog.style.width = "96%";
    dialogbody.appendChild(singleDialog);
    var paralen;
    if (d.type && d.character) {
        updateCompanyWorking(d.character);
        var renderedHtml = md.render(d.character);
        const character = document.createElement("div");
        character.style.display = "flex";

        character.style.backgroundColor = "lightblue";
        character.style.width = "fit-content";
        character.style.padding = "5px 20px";
        character.style.marginBottom = "5px";
        character.style.fontSize = "13px";
        character.style.border = "1px solid rgba(11, 20, 150, .3)";
        character.style.borderRadius = "10px";
        character.style.boxShadow = "2px 2px 2px black";
        character.style.fontFamily = "'Lucida Sans', 'Lucida Sans Regular', 'Lucida Grande', 'Lucida Sans Unicode', Geneva, Verdana, sans-serif";
        if (d.type == "user") {
            character.style.position = "relative";
            character.style.marginLeft = "auto";
        }
        character.innerHTML = renderedHtml;
        singleDialog.appendChild(character);

        const characterimg = document.createElement("img");
        console.log(d.character);
        if (d.character == "Programmer") {
            characterimg.src = "figures/programmer.png";
        } else if (d.character == "System") {
            characterimg.src = "figures/System.png";
        } else if (d.character == "HTTP Request") {
            characterimg.src = "figures/http.png";
        } else if (d.character == "Code Reviewer") {
            characterimg.src = "figures/reviewer.png";
        } else if (d.character == "Chief Human Resource Officer") {
            characterimg.src = "figures/hr.png";
        } else if (d.character == "Chief Executive Officer") {
            characterimg.src = "figures/ceo.png";
        } else if (d.character == "Chief Product Officer") {
            characterimg.src = "figures/cpo.png";
        } else if (d.character == "Chief Technology Officer") {
            characterimg.src = "figures/cto.png";
        } else if (d.character == "Chief Creative Officer") {
            characterimg.src = "figures/designer.png";
        } else if (d.character == "Software Test Engineer") {
            characterimg.src = "figures/tester.png";
        } else if (d.character == "User") {
            characterimg.src = "figures/user.png";
        } else if (d.character == "Counselor") {
            characterimg.src = "figures/counselor.png";
        } else if (d.character == "Prompt Engineer") {
            characterimg.src = "figures/pe.png";
        }

        characterimg.style.height = "40px";
        characterimg.style.width = "30px";
        characterimg.style.position = "relative";
        characterimg.style.marginLeft = "10px";
        character.appendChild(characterimg);
        character.style.width = "fit-content";


        var renderedHtml = md.render(d.command);
        const paragraph = document.createElement("div");
        paragraph.className = "markdown-body";
        paragraph.innerHTML = renderedHtml;
        paragraph.style.padding = "10px";
        paragraph.style.border = "3px solid #a08D8D";
        paragraph.style.width = "750px";
        paragraph.style.marginLeft = "0.4rem";
        paragraph.style.border = "1px solid rgba(11, 20, 150, .3)";
        paragraph.style.borderRadius = "10px";
        paragraph.style.boxShadow = "2px 2px 2px black";

        singleDialog.appendChild(paragraph);

        const emptyparagraph = document.createElement("div");
        emptyparagraph.style.height = "10px";
        singleDialog.appendChild(emptyparagraph);

        if (d.type == "user") {
            paragraph.style.backgroundColor = "#a02D8D";
        } else {
            paragraph.style.backgroundColor = "#133153";
        }
        cur_command = d.command;
        cur_para = paragraph;
        idx = i;
        return Promise.resolve(printCommand(paragraph, d.command));

    } else if (d.start) {
        paralen = 0;
        var renderedHtml = md.render("----------" + d.start + "----------");
        const starttext = document.createElement("div");
        starttext.innerHTML = renderedHtml;
        singleDialog.appendChild(starttext);

    } else if (d.end) {
        paralen = 0;
        updateCompanyWorking("end");
        var renderedHtml = md.render("----------" + d.end + "----------");
        const endtext = document.createElement("div");
        endtext.innerHTML = renderedHtml;
        singleDialog.appendChild(endtext);
        var filelable = document.getElementById("successupload");
        filelable.style.display = "block";
        var info = "Replayed";
        filelable.innerHTML = md.render(info);
    } else if (d.task) {
        var renderedHtml = md.render("Task:    " + d.task);
        const tasktext = document.getElementById("Requesttext");
        tasktext.innerHTML = renderedHtml;
    } else if (d.info) {
        var renderedHtml = md.render(d.info);
        const infotext = document.getElementById("dialogStatistic");
        var temp_label = "";
        for (var c in Softwareinfo) {
            temp_label = document.getElementById(c);
            if (Softwareinfo[c] != "-1" && Softwareinfo[c] != "-1s") {
                temp_label.innerHTML = Softwareinfo[c];
            }
        }
    }
}

//update company image
function updateCompanyWorking(character) {
    if (character === "end") {
        var img1 = document.getElementById("right");
        var img2 = document.getElementById("left");
        if (img1) img1.style.display = "none";
        if (img2) img2.style.display = "none";
        return;
    }

    const characterConfig = coordSet[character];
    if (!characterConfig) {
        console.error(`Character '${character}' is not defined in coordSet.`);
        return;
    }

    var imgid = characterConfig.imgid;
    var left_bias = characterConfig.left;
    var top_bias = characterConfig.top;
    var img = document.getElementById(imgid);

    if (!img) {
        console.error(`Image element with id '${imgid}' not found.`);
        return;
    }

    img.style.display = "block";
    img.style.left = left_bias;
    img.style.top = top_bias;

    var another_img = document.getElementById(imgid === "left" ? "right" : "left");
    if (another_img) another_img.style.display = "none";
}

async function updateParashow(container, command, index, len) {
    var cur_content;
    if (index == len - 1) {
        cur_content = command.slice(0, index);
    }
    if (index < len) {
        cur_content = command.slice(0, index);
        if (cur_content != null && cur_content != undefined) {
            container.innerHTML = md.render(cur_content);
        };
    }
    if (index % (config.scrollinterval) == 0 && if_move == true) {
        if (curdialog != null && curdialog != '') {
            const newBoxRect = curdialog.getBoundingClientRect();
            total_height += newBoxRect.height;
            dialogbody.scrollTo({ top: total_height, behavior: 'smooth' });
        }
    }
}

async function printCommand(paragraph, command) {
    var paralen = command.length;
    const tasks = [];

    for (let j = 0; j < paralen; j = j + config.charinterval) {
        tasks.push(new Promise(resolve => {
            pauseIntervalId = setTimeout(() => {
                updateParashow(paragraph, command, j, paralen);
                resolve();
            }, config.timeinterval * j);
        }));

        if (isPaused) {
            await Promise.all(tasks);
        }
    }
    await Promise.all(tasks);
    return 1;
}
