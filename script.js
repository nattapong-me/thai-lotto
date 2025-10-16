const apiListUrl = 'https://lotto.api.rayriffy.com/list/1';
const apiLottoUrl = 'https://lotto.api.rayriffy.com';
const select = document.getElementById('lottoDate');
const resultDiv = document.getElementById('result');
const input = document.getElementById('lottoNumber');
const btn = document.getElementById('checkBtn');
let lottoCache = {}; // เก็บข้อมูลงวดที่โหลดมาแล้ว

// โหลดรายการงวดทั้งหมด
async function loadLottoList() {
  const res = await fetch(apiListUrl);
  const data = await res.json();
  const list = data.response || [];

  list.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.url;
    opt.textContent = item.date;
    select.appendChild(opt);
  });


    // ✅ ตั้งค่า default เป็นงวดล่าสุด (รายการแรก)
  const latest = list[0];
  select.value = latest.url;
}

// ดึงผลลอตเตอรี่จาก API (มี cache)
async function getLottoResult(date) {
  if (lottoCache[date]) return lottoCache[date];
  const res = await fetch(apiLottoUrl + date);
  const data = await res.json();
  lottoCache[date] = data.response;
  return data.response;
}

// ตรวจรางวัล
function checkPrize(userNum, lotto) {
  const prizes = lotto.prizes || [];
  const running = lotto.runningNumbers || [];
  let messages = [];

  // ตรวจรางวัลหลักทั้งหมด
  prizes.forEach(prize => {
    if (prize.number.includes(userNum)) {
      messages.push(`🎉 ถูกรางวัล${prize.name} (${Number(prize.reward).toLocaleString()} บาท)`);
    }
  });

  // ตรวจรางวัลเลขหน้า 3 ตัว / เลขท้าย 3 ตัว / เลขท้าย 2 ตัว
  const first3 = userNum.slice(0, 3);
  const last3 = userNum.slice(-3);
  const last2 = userNum.slice(-2);

  running.forEach(run => {
    if (run.id === "runningNumberFrontThree" && run.number.includes(first3)) {
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
    }
    if (run.id === "runningNumberBackThree" && run.number.includes(last3)) {
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
    }
    if (run.id === "runningNumberBackTwo" && run.number.includes(last2)) {
      messages.push(`🎉 ถูกรางวัล${run.name} (${Number(run.reward).toLocaleString()} บาท)`);
    }
  });

  if (messages.length === 0) {
    messages.push("❌ ไม่ถูกรางวัล");
  }

  return messages.join("<br>");
}


// เมื่อกดตรวจรางวัล
btn.addEventListener('click', async () => {
  const date = select.value;
  const num = input.value.trim();

  if (!date) {
    alert('กรุณาเลือกงวดก่อน');
    return;
  }
  if (!/^\d{6}$/.test(num)) {
    alert('กรุณากรอกเลข 6 หลักให้ถูกต้อง');
    return;
  }

  resultDiv.innerHTML = '⏳ กำลังตรวจสอบ...';

  const lotto = await getLottoResult(date);
  console.log('done get data')
  if (!lotto) {

    resultDiv.innerHTML = '<p>ไม่พบข้อมูลงวดนี้</p>';
    return;
  }

  const result = checkPrize(num, lotto);
  console.log(result)
// สร้าง HTML แสดงรางวัล
let prizeHtml = `
  <h2 class="${result.includes('ไม่ถูกรางวัล') ? 'result-lose' : 'result-win'}" 
      style="font-size: 28px; text-align: center; margin-bottom: 20px;">
      ${result}
  </h2>
  
  <h3>ผลสลากกินแบ่งรัฐบาล งวดวันที่ ${lotto.date}</h3>
  <h4>รางวัลหลัก</h4>
  <table style="width:100%; border-collapse: collapse;">
    <thead>
      <tr style="background:#f0f0f0;">
        <th style="border:1px solid #ccc; padding:8px;">ชื่อรางวัล</th>
        <th style="border:1px solid #ccc; padding:8px;">หมายเลขที่ถูกรางวัล</th>
      </tr>
    </thead>
    <tbody>
      ${lotto.prizes.map(p => `
        <tr>
          <td style="border:1px solid #ccc; padding:8px;">${p.name}</td>
          <td style="border:1px solid #ccc; padding:8px;">${p.number.join(', ')}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>

  <h4 style="margin-top:20px;">รางวัลเลขหน้า / เลขท้าย</h4>
  <table style="width:100%; border-collapse: collapse;">
    <thead>
      <tr style="background:#f0f0f0;">
        <th style="border:1px solid #ccc; padding:8px;">ชื่อรางวัล</th>
        <th style="border:1px solid #ccc; padding:8px;">หมายเลขที่ถูกรางวัล</th>
      </tr>
    </thead>
    <tbody>
      ${lotto.runningNumbers.map(r => `
        <tr>
          <td style="border:1px solid #ccc; padding:8px;">${r.name}</td>
          <td style="border:1px solid #ccc; padding:8px;">${r.number.join(', ')}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
`;

resultDiv.innerHTML = prizeHtml;
});

// โหลดงวดเมื่อเปิดหน้า
loadLottoList();