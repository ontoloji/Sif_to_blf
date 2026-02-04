# SIF to BLF Converter v2.0

Somat eDAQ SIF dosyalarını Vector BLF formatına dönüştürür - **DBC Desteği ile!**

## 🎯 Yeni Özellikler v2.0

✅ **DBC Desteği**: CAN database dosyaları ile signal encoding  
✅ **Dual Output**: Hem signal grafikler hem raw CAN mesajları  
✅ **ENV_DOUBLE Objects**: CANalyzer Data Window desteği  
✅ **CAN_MESSAGE2 Objects**: CANalyzer Trace Window desteği  
✅ **Auto Signal Mapping**: SIF kanallarını DBC signallerine otomatik eşleme  
✅ **Multi-DBC Support**: Birden fazla DBC dosyası desteği

## 📋 Gereksinimler

- Python 3.7 veya üzeri  
- Standart Python kütüphaneleri (harici dependency yok!)  
- DBC dosyaları (Foton_CAN1.dbc, Foton_CAN2_v2.dbc, PCAN.dbc vb.)

## 🚀 Kurulum

```bash
# Repository'yi klonla
git clone https://github.com/ontoloji/Sif_to_blf.git
cd Sif_to_blf

# Dosyalar hazır!
```

## 📖 Kullanım

### v2.0 - DBC Desteği ile (ÖNERİLEN)

```bash
# Tek DBC dosyası
python sif_to_blf_converter_v2.py ornek_sif.sif output.blf -d Foton_CAN1.dbc

# Birden fazla DBC
python sif_to_blf_converter_v2.py ornek_sif.sif output.blf -d Foton_CAN1.dbc Foton_CAN2_v2.dbc PCAN.dbc

# Wildcard ile tüm DBC'ler
python sif_to_blf_converter_v2.py ornek_sif.sif output.blf -d *.dbc

# Verbose mod
python sif_to_blf_converter_v2.py ornek_sif.sif output.blf -d *.dbc -v
```

### v1.0 - DBC Olmadan (Eski Versiyon)

```bash
python sif_to_blf_converter.py ornek_sif.sif output.blf
```

## 📂 Dosya Yapısı

```
Sif_to_blf/
├── sif_parser.py                  # SIF dosyası parser
├── dbc_parser.py                  # DBC dosyası parser (YENİ!)
├── blf_writer.py                  # Vector BLF writer (ENV_DOUBLE desteği)
├── sif_to_blf_converter.py       # v1.0 - Basit converter
├── sif_to_blf_converter_v2.py    # v2.0 - DBC destekli converter (YENİ!)
├── requirements.txt               # Boş (dependency yok)
├── README.md                      # Bu dosya
└── ornek_sif.sif                 # Örnek SIF dosyası
```

## 🎓 CANalyzer'da Görüntüleme

### A) Signal Grafikler (ENV_DOUBLE)

1. CANalyzer'da BLF dosyasını açın
2. **Data Window** → **Configuration** → **Add Channel**
3. Kanalları görün: `CompIn_P`, `Amb_T`, `lat`, `lon` vb.
4. **Graphics Window** ile grafik çizin

### B) Raw CAN Mesajları (CAN_MESSAGE2)

1. CANalyzer'da BLF dosyasını açın
2. **Trace Window** → CAN mesajlarını görün
3. DBC dosyasını yükleyin: **Configuration** → **Database** → **Add**
4. Mesajlar otomatik decode edilir!

## 🔍 Nasıl Çalışır?

```
┌─────────────┐
│  SIF File   │  ← Decoded signal values (CompIn_P = 1234.5 mbar)
└──────┬──────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────┐                 ┌──────────────┐
│ ENV_DOUBLE   │                 │ DBC Parser   │
│   Objects    │                 │   Encoder    │
└──────┬───────┘                 └──────┬───────┘
       │                                 │
       │                                 ▼
       │                         ┌──────────────┐
       │                         │CAN_MESSAGE2  │
       │                         │   Objects    │
       │                         └──────┬───────┘
       │                                 │
       └─────────────┬───────────────────┘
                     ▼
              ┌─────────────┐
              │  BLF File   │  ← CANalyzer'da açılır
              └─────────────┘
```

## 📊 Örnek Çıktı

```bash
$ python sif_to_blf_converter_v2.py ornek_sif.sif test.blf -d *.dbc

🎯 SIF to BLF Converter v2.0 with DBC Support

🔍 Parsing SIF file: ornek_sif.sif
✅ SIF Version: v3.17.0 build 461
✅ Found 3 CAN interfaces
✅ Found 36 channels

📚 Loading DBC files...
   📖 Loading: Foton_CAN1.dbc
      ✅ 45 messages, 234 signals
   📖 Loading: Foton_CAN2_v2.dbc
      ✅ 38 messages, 187 signals
   📖 Loading: PCAN.dbc
      ✅ 12 messages, 56 signals

📡 CAN Interfaces:
   CAN_1: 500000 bps
      DBs: PCAN
   CAN_2: 500000 bps
      DBs: PCAN
   CAN_3: 250000 bps
      DBs: Foton_CAN1, Foton_CAN2_v2

📊 Channels (first 10):
   1. CompIn_P (Pressure) - mbar, 100 Hz
   2. CompOut_P (Pressure) - mbar, 100 Hz
   3. ESS_IAPU41_P (Pressure) - mbar, 100 Hz
   4. AirDryIn_P (Pressure) - mbar, 100 Hz
   5. BrkChmbr_P (Pressure) - mbar, 100 Hz
   ...

🔄 Converting to BLF format...
📦 Binary data size: 5,797,459 bytes
⚙️  Processing 1000 sample points...
   Sample rate: 100 Hz (10000.0 μs interval)
   Matched 28/36 channels to DBC signals
   Progress: 100/1000
   Progress: 200/1000
   ...
💾 Writing BLF file: test.blf

✅ Conversion completed!
📊 Generated 29,000 BLF objects

📈 CANalyzer'da görüntüleme:
   A) Signal grafikler: Data Window → Channels
   B) Raw CAN mesajları: Trace Window → CAN messages
```

## 🔧 DBC Parser Özellikleri

### Desteklenen DBC Formatı

```dbc
BO_ 1234 MessageName: 8 SenderNode
 SG_ SignalName : 0|16@1+ (0.1,0) [0|6553.5] "bar" ReceiverNode
```

### Signal Encoding

- ✅ Little Endian (Intel) - `@1`
- ✅ Big Endian (Motorola) - `@0`
- ✅ Signed/Unsigned - `+` / `-`
- ✅ Scale & Offset - `(0.1, 0)`
- ✅ Min/Max validation

### Auto Mapping

SIF kanallarını DBC signallerine otomatik eşler:
- Exact match: `CompIn_P` → `CompIn_P`
- Fuzzy match: `CompIn_P` → `COMPIN_P`, `CompInP`
- Prefix handling: `ESS.CompIn_P` → `CompIn_P`

## ⚠️ Önemli Notlar

### Binary Data Decoding

⚠️ **SIF binary format henüz tam decode edilmiyor**

Şu anda:
- ✅ SIF metadata parse ediliyor (CAN interfaces, channels, calibration)
- ✅ DBC signal encoding çalışıyor
- ⚠️ Binary data kısmı **placeholder** kullanıyor (synthetic data)

Gerçek veri dönüşümü için:
1. SIF binary format dokümantasyonu gerekli
2. Farklı SIF dosyaları ile pattern analizi
3. `_extract_sample_data()` metodunun güncellenmesi

### Sorun Giderme

**❌ "No module named 'dbc_parser'"**
```bash
# Güncel dosyaları çekin
git pull origin main
```

**❌ "DBC file not found"**
```bash
# DBC dosyalarını aynı klasöre koyun veya tam yol verin
python sif_to_blf_converter_v2.py input.sif output.blf -d C:\path\to\file.dbc
```

**❌ "Matched 0/36 channels to DBC signals"**
- SIF kanal isimleri ile DBC signal isimleri eşleşmiyor
- Verbose mode ile kontrol edin: `-v`
- Manuel mapping eklenebilir

## 🛠️ Geliştirme Yol Haritası

### Faz 1: Binary Format (Öncelik 1)
- [ ] SIF binary format analizi
- [ ] Gerçek veri decode
- [ ] Timestamp extraction
- [ ] Multi-channel synchronization

### Faz 2: İyileştirmeler
- [ ] Progress bar
- [ ] Multi-threading
- [ ] Memory optimization
- [ ] Büyük dosya desteği (>1GB)

### Faz 3: Ek Özellikler
- [ ] GPS data extraction
- [ ] CAN FD support
- [ ] LIN bus support
- [ ] FlexRay support

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch: `git checkout -b feature/amazing`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing`
5. Pull Request açın

## 📄 Lisans

MIT License

## 👤 İletişim

- **Repository**: [ontoloji/Sif_to_blf](https://github.com/ontoloji/Sif_to_blf)
- **Issues**: [GitHub Issues](https://github.com/ontoloji/Sif_to_blf/issues)

## 🙏 Teşekkürler

- Somat (HBM) - SIF format
- Vector - BLF format specification
- Python Community

---

⭐ Faydalı bulduysanız yıldız vermeyi unutmayın!