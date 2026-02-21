const HOST = "https://algocourses.ru"

async function fetch_data() {
    var locs = window.location.pathname.split('/').filter(Boolean);
    var table_name = locs.pop();
    locs.pop();
    var course_name = locs.pop();

    console.log(location)

    const response = await fetch(`${HOST}/api/standings/${course_name}/${table_name}`);
    if (response.status !== 200) {
        window.location = "/";
    }
    return await response.json();
}

function valueToColor(value) {
    const t = Math.max(0, Math.min(1, value / 100)); // нормализуем 0–1

    const r1 = 240, g1 = 128, b1 = 128;
    const r2 = 144, g2 = 238, b2 = 144;

    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);

    return `rgb(${r}, ${g}, ${b})`;
}


function set_thead(cols, contests) {
    const thead = document.getElementById('thead');

    var base = [];
    var tasks = [];
    for (let c of cols) {
        base.push(`<th rowspan="2" colspan="1" class="unmovable-header">${c}</th>`);
    }

    for (let contest of contests) {
        base.push(`<th class="movable-header" colspan="${contest.problems.length + 1}">${contest.name}</th>`)
        for (let task of contest.problems) {
            tasks.push(`<th class="cell-item movable-header" title="${task.long}">${task.short}</th>`)
        }
        tasks.push(`<th class="cell-item movable-header">Σ</th>`)
    }

    thead.innerHTML = `<tr>${base.join('')}</tr> <tr>${tasks.join('')}</tr>`
}

async function main() {
    data = await fetch_data();
    const base_cols = ["Место", "Имя", "Решено"];
    const cols_props = ["place", "name", "score"];

    const tbody = document.getElementById('tbody');
    const thead = document.getElementById('thead');

    set_thead(base_cols, data.contests);

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }

    function render() {
        let html = '';
        for (let vi = 0; vi < data["standings"].length; vi++) {
            const row = data["standings"][vi];
            html += '<tr>';
            for (let c of cols_props) {
                const v = row[c];
                html += `<td title="${escapeHtml(v)}" style="position: sticky">${escapeHtml(v)}</td>`;
            }
            var idx = 0;
            for (let contest of row.per_contests) {
                if (contest.tasks === null) {
                    for (let i = 0; i < data.contests[idx].problems.length; i += 1) {
                        html += `<td class="cell-item"></td>`;
                    }
                } else {
                    for (let i = 0; i < contest.tasks.length; i += 1) {
                        let item = contest.tasks[i];
                        let upsolving = contest.upsolving[i];
                        const style = ""
                        if (data.contests[idx].is_acm) {
                            const good_name = (item > 0 ? 'ok' : 'upsolved')
                            const bad_name = (item === upsolving ? 'bad' : 'not_upsolved')
                            if (item <= 0 && item !== upsolving) {
                                item = upsolving;
                            }

                            if (item === 0) {
                                html += `<td class="cell-item"></td>`;
                                continue;
                            }
                            const classname = item > 0 ? good_name : bad_name
                            // console.log(item)
                            const text = item > 0 ? "+" : "-";
                            var penalty = "";
                            var real_penalty = "";
                            var penalty_val = Math.abs(item) - (item > 0 ? 1 : 0);
                            if (penalty_val > 0) {
                                real_penalty = penalty_val;
                                if (penalty_val >= 10) {
                                    penalty = "∞";
                                } else {
                                    penalty = penalty_val;
                                }
                            }
                            html += `<td class="${classname} cell-item" style="${style}" title="${text}${real_penalty}">${text}${penalty}</td>`;
                        } else {
                            if (item === -1) {
                                html += `<td class="cell-item"></td>`;
                                continue;
                            }
                            const classname = item === 100 ? 'ok' : 'bad';
                            html += `<td class="${classname} cell-item" style="${style}; background-color: ${valueToColor(item)}" title="${item}">${item}</td>`;
                        }
                    }
                }
                idx += 1;
                html += `<td class="cell-item">${contest.score}</td>`;
            }
            html += '</tr>';
        }

        tbody.innerHTML = html;

        var prefsum = 0;

        for (let i = 0; i < base_cols.length; ++i) {
            const head_item = thead.children[0].children[i];
            const width = head_item.getBoundingClientRect().width;

            for (var x of tbody.children) {
                x.children[i].style["left"] = prefsum + "px";
            }

            head_item.style["left"] = prefsum + "px";
            prefsum += width;
        }
    }

    render();
    document.getElementsByClassName("loader")[0].remove()
}

window.onload = async function () {
    await main();
    document.getElementById("table-wrap").focus();
};