// ชี้ไปที่ไฟล์ JSON ที่ GitHub Actions scrape มาแล้ว
const DATA_BASE = './data';

const select = document.getElementById('lottoDate');
const resultDiv = document.getElementById('result');
const input = document.getElementById('lottoNumber');
const btn = document.getElementById('checkBtn');
let lottoCache = {};

// โหลดรายการงวดจาก data/list.json
async function loadLottoList() {
  select.innerHTML = '<option value="">⏳ กำลังโหลด...</option>';
  try {
    const res = await fetch(`${DATA_BASE}/list.json`);
    if (!res.ok) throw new Error('ไม่พบไฟล์ list.json');
    const data = await res.json();
    const list = data.response || [];

    select.innerHTML = '<option value="">-- กรุณาเลือกงวด --</option>';
    list.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.id;
      opt.textContent = item.date;
      select.appendChild(opt);
    });

    if (list.length > 0) select.value = list[0].id;
  } catch (e) {
    select.innerHTML = '<option value="">❌ โหลดรายการไม่ได้</option>';
    resultDiv.innerHTML = `<p style="color:red">ยังไม่มีข้อมูล กรุณารัน GitHub Actions ก่อน</p>`;
    console.error(e);
  }
}

// ดึงผลลอตเตอรี่จากไฟล์ JSON (มี cache)
async function getLottoResult(id) {
  if (lottoCache[id]) return lottoCache[id];
  const res = await fetch(`${DATA_BASE}/${id}.json`);
  if (!res.ok) throw new Error(`ไม่พบข้อมูลงวด ${id}`);
  const data = await res.json();
  lottoCache[id] = data.response;
  return data.response;
}

// ตรวจรางวัล
function checkPrize(userNum, lotto) {
  const prizes = lotto.prizes || [];
  const running = lotto.runningNumbers || [];
  let messages = [];

  prizes.forEach(prize => {
    if (prize.number.includes(userNum))
      messages.push(`🎉 ถูกรางวัล${prize.name} (${Number(prize.reward).toLocaleString()} บาท)`);
  });

  const first3 = userNum.slice(0, 3);
  const last3 = userNum.slice(-3);
  const last2 = userNum.slice(-2);

  running.forEach(run => {
    if (run.id === 'runningNumberFrontThree' && run.number.includes(first3))
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
    if (run.id === 'runningNumberBackThree' && run.number.includes(last3))
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
    if (run.id === 'runningNumberBackTwo' && run.number.includes(last2))
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
  });

  if (messages.length === 0) messages.push('❌ ไม่ถูกรางวัล');
  return messages.join('<br>');
}

// เมื่อกดตรวจรางวัล
btn.addEventListener('click', async () => {
  const id = select.value;
  const num = input.value.trim();

  if (!id) { alert('กรุณาเลือกงวดก่อน'); return; }
  if (!/^\d{6}$/.test(num)) { alert('กรุณากรอกเลข 6 หลักให้ถูกต้อง'); return; }

  resultDiv.innerHTML = '⏳ กำลังตรวจสอบ...';

  try {
    const lotto = await getLottoResult(id);
    if (!lotto) { resultDiv.innerHTML = '<p>ไม่พบข้อมูลงวดนี้</p>'; return; }

    const result = checkPrize(num, lotto);

    resultDiv.innerHTML = `
      <h2 class="${result.includes('ไม่ถูกรางวัล') ? 'result-lose' : 'result-win'}"
          style="font-size:28px;text-align:center;margin-bottom:20px;">
        ${result}
      </h2>
      <h3>ผลสลากกินแบ่งรัฐบาล งวดวันที่ ${lotto.date}</h3>
      <h4>รางวัลหลัก</h4>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#f0f0f0;">
            <th style="border:1px solid #ccc;padding:8px;">ชื่อรางวัล</th>
            <th style="border:1px solid #ccc;padding:8px;">หมายเลขที่ถูกรางวัล</th>
          </tr>
        </thead>
        <tbody>
          ${lotto.prizes.map(p => `
            <tr>
              <td style="border:1px solid #ccc;padding:8px;">${p.name}</td>
              <td style="border:1px solid #ccc;padding:8px;">${p.number.join(', ')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      <h4 style="margin-top:20px;">รางวัลเลขหน้า / เลขท้าย</h4>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#f0f0f0;">
            <th style="border:1px solid #ccc;padding:8px;">ชื่อรางวัล</th>
            <th style="border:1px solid #ccc;padding:8px;">หมายเลขที่ถูกรางวัล</th>
          </tr>
        </thead>
        <tbody>
          ${lotto.runningNumbers.map(r => `
            <tr>
              <td style="border:1px solid #ccc;padding:8px;">${r.name}</td>
              <td style="border:1px solid #ccc;padding:8px;">${r.number.join(', ')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:red">❌ ${e.message}</p>`;
  }
});

loadLottoList();