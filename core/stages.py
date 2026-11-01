"""Crop growth stages by days after sowing (transplanting for paddy).
ASSUMPTIONS: typical durations and tips for general guidance. They vary by variety, sowing date and region.
Confirm with your Krishi Vigyan Kendra (KVK) or state agriculture university and cite them in your submission."""
from datetime import date, datetime, timedelta

# (start_day, name_en, name_hi, water_need, tip_en, tip_hi)   water_need: critical, high, medium, low
CYCLE = {
 "wheat": {"maturity": 130, "stages": [
  (0, "Germination", "अंकुरण", "medium", "Make sure the seed has enough moisture to germinate. A light irrigation helps if the field is dry.", "बीज को अंकुरण के लिए नमी चाहिए। खेत सूखा हो तो हल्की सिंचाई करें।"),
  (20, "Crown root initiation", "ताज जड़ अवस्था", "critical", "Best time for the first irrigation. Irrigate if the soil is dry.", "पहली सिंचाई के लिए सबसे ज़रूरी समय। मिट्टी सूखी हो तो सिंचाई करें।"),
  (40, "Tillering", "कल्ले फूटना", "high", "Weed control and nitrogen top-dressing (as per soil test) help most now.", "अभी निराई और मिट्टी जांच के अनुसार नाइट्रोजन देना सबसे फायदेमंद है।"),
  (60, "Jointing", "तना बढ़ना", "high", "Keep the soil moist. Look for yellow or orange rust patches on leaves.", "मिट्टी में नमी रखें। पत्तियों पर पीले या नारंगी रतुआ के धब्बे देखते रहें।"),
  (80, "Flowering", "फूल आना", "critical", "Avoid water stress. Heat above 35 C can reduce grain set.", "पानी की कमी न होने दें। 35 डिग्री से ऊपर गर्मी से दाने कम बन सकते हैं।"),
  (100, "Grain filling", "दाना भरना", "critical", "Irrigate lightly if dry. Avoid irrigating in strong wind, the crop can lodge.", "सूखा हो तो हल्की सिंचाई करें। तेज़ हवा में सिंचाई न करें, फसल गिर सकती है।"),
  (118, "Ripening", "पकना", "low", "Stop irrigation. Arrange labour, machine and storage for harvest.", "सिंचाई बंद करें। कटाई के लिए मज़दूर, मशीन और भंडारण की तैयारी करें।")]},
 "paddy": {"maturity": 125, "stages": [
  (0, "Recovery after transplanting", "रोपाई के बाद जड़ें जमना", "high", "Keep a thin film of water in the field.", "खेत में पानी की पतली परत रखें।"),
  (12, "Tillering", "कल्ले फूटना", "high", "Control weeds and give nitrogen as per soil test. Keep shallow water.", "निराई करें और मिट्टी जांच के अनुसार नाइट्रोजन दें। कम पानी रखें।"),
  (42, "Panicle initiation", "बाली बनना शुरू", "high", "Do not let the field dry. Watch for leaf blast and stem borer.", "खेत सूखने न दें। झोंका रोग और तना छेदक पर नज़र रखें।"),
  (65, "Flowering", "फूल आना", "critical", "Water stress now cuts yield the most. Keep water in the field.", "अभी पानी की कमी से उपज सबसे ज़्यादा घटती है। खेत में पानी रखें।"),
  (85, "Grain filling", "दाना भरना", "high", "Maintain moisture. Drain the field about 10 days before harvest.", "नमी बनाए रखें। कटाई से करीब 10 दिन पहले पानी निकाल दें।"),
  (105, "Ripening", "पकना", "low", "Stop irrigation. Harvest when most grains in the panicle are straw coloured.", "सिंचाई बंद करें। बाली के ज़्यादातर दाने भूसे जैसे रंग के हों तब कटाई करें।")]},
 "maize": {"maturity": 105, "stages": [
  (0, "Germination", "अंकुरण", "medium", "Check the plant stand. Re-sow gaps within about a week.", "पौधों की संख्या देखें। खाली जगह लगभग एक हफ्ते में दोबारा बोएं।"),
  (12, "Vegetative growth", "बढ़वार", "medium", "Weed early and top-dress nitrogen as per soil test.", "जल्दी निराई करें और मिट्टी जांच के अनुसार नाइट्रोजन दें।"),
  (45, "Tasseling and silking", "झंडा और रेशे निकलना", "critical", "Most sensitive to water and heat stress. Do not skip irrigation if dry.", "पानी और गर्मी की कमी के प्रति सबसे संवेदनशील। सूखा हो तो सिंचाई न छोड़ें।"),
  (65, "Grain filling", "दाना भरना", "high", "Keep the soil moist. Look for leaf blight and rust.", "नमी रखें। पत्ती झुलसा और रतुआ देखें।"),
  (90, "Maturity", "पकना", "low", "Harvest when husks dry and grains harden. Dry cobs well before storage.", "छिलके सूखें और दाने सख्त हों तब कटाई करें। भंडारण से पहले भुट्टे अच्छी तरह सुखाएं।")]},
 "mustard": {"maturity": 120, "stages": [
  (0, "Germination", "अंकुरण", "medium", "Thin crowded plants about 2 weeks after sowing.", "बुवाई के लगभग 2 हफ्ते बाद घने पौधे विरल करें।"),
  (18, "Rosette", "रोज़ेट अवस्था", "medium", "Control weeds. Give the first irrigation at about 30 to 35 days if dry.", "निराई करें। सूखा हो तो करीब 30 से 35 दिन पर पहली सिंचाई करें।"),
  (38, "Flower initiation", "फूल बनना शुरू", "high", "Keep moisture. Check shoots for aphids.", "नमी रखें। टहनियों पर माहू (एफिड) देखें।"),
  (50, "Flowering", "फूल आना", "critical", "Avoid water stress and watch aphids closely. Frost can damage flowers.", "पानी की कमी न होने दें, माहू पर नज़र रखें। पाला फूलों को नुकसान पहुंचा सकता है।"),
  (75, "Pod filling", "फलियां भरना", "critical", "A light irrigation helps pod filling if the field is dry.", "सूखा हो तो हल्की सिंचाई से फलियां अच्छी भरती हैं।"),
  (100, "Ripening", "पकना", "low", "Harvest when most pods turn yellow-brown, to reduce shattering losses.", "ज़्यादातर फलियां पीली-भूरी हों तब कटाई करें, ताकि दाने झड़ने का नुकसान कम हो।")]},
}
WATER_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
DEFAULT_YIELD_QTL_ACRE = {"wheat": 16, "paddy": 18, "maize": 14, "mustard": 6}   # typical, farmer should edit


def stage_info(crop, sowing_date, today=None):
    """Where the crop is today. sowing_date is 'YYYY-MM-DD'."""
    today = today or date.today()
    sow = datetime.strptime(sowing_date, "%Y-%m-%d").date()
    cyc = CYCLE[crop]
    das = (today - sow).days
    out = {"das": das, "maturity_days": cyc["maturity"], "sowing": sow,
           "maturity_date": sow + timedelta(days=cyc["maturity"])}
    out["days_to_maturity"] = (out["maturity_date"] - today).days
    if das < 0:
        out.update(phase="not_sown", stage=None, next=cyc["stages"][0], days_to_next=-das, progress=0.0)
        return out
    idx = max(i for i, st in enumerate(cyc["stages"]) if st[0] <= das)
    cur = cyc["stages"][idx]
    nxt = cyc["stages"][idx + 1] if idx + 1 < len(cyc["stages"]) else None
    out.update(stage_index=idx, stage={"start": cur[0], "en": cur[1], "hi": cur[2], "water": cur[3], "tip_en": cur[4], "tip_hi": cur[5]},
               next=nxt, days_to_next=(nxt[0] - das) if nxt else None,
               progress=round(min(1.0, das / cyc["maturity"]), 3))
    d2m = out["days_to_maturity"]
    out["phase"] = "overdue" if d2m < -7 else "harvest" if d2m <= 10 else "growing"
    return out
