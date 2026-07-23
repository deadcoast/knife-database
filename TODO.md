# KNIFE DATABASE 4 - RAW NOTES

-------------------------------
> [!NOTE]
> Feature Additions Dependency Graph
> Requires upkeep and further additions missed

```json
{
  "FEATURE_ADDITIONS":"REQUIREMENTS":[
      "new",
      "update",
      "add",
      "section",
      "markdown-ingestion-file",
      "BuyList",
      "SectionLineIndicators",
      "SectionID"
      "commands",
      "flags"
    ]
}
```

> Feature Additions

- `update`
  - example: `knivves update`: an update command that refreshes the database, tagging new entries as *NEW*. This will be the line that is decided what to tag *NEW* or not.
- `add`
  - `knivves add <path/to/file.md>`: the knivves db should be able to parse - `[knife ID and reference number](https://link-to-the-knife-model)` These can sometimes be tricky, as websites like to add round brackets for the reference number`()`. DEPENDING ON HOW YOU DEVELOP THIS, THESE CAN BE PROBLEMATIC. IT MAY BE WISE TO REMOVE and REPLACE the ROUND BRACKETS with a DASH to SEPERATE the Knife ID and the Reference Number, like so:[REF2]
  - THE GOAL of this, is to point the CLI to a markdown file with links in it. The format can be seen at [REF1]. This format was created to provide dense links, while also providing clear seperation. I chose to add longer lines at 31 dash(`-`) characters, so we can identify exactly the number of dashes for the title heading line seperators in parsing. THE 31 CHARACTER LINES ARE USED FIRST AND FOREMOST, TO SEPERATE AREAS AND MAKE LONG LISTS MORE INGESTIBLE, TO STREAMLINE THE TAGGING PROCESS OF KNIVES, AND TO MAKE IT EASIER FOR USERS TO ADD THEIR DATA, AND HAVE IT UPDATED LIVE IN THE CLI. IT ADDES A MORE COMPLETE ECOSYSTEM. IN USE THE `SLI` LINES INDICATE THAT BETWEEN THE 31 CHARACTER SEPERATORS ARE RELATED DATA, GROUPS, AND THAT THEY MOST LIKELY HAVE A `SectionID`;[REF2]
- `section`(`SectionID`)
  - example: `knivves list -section`
  - `SectionID`: THIS ASSIGNMENT WORD FORMALLY REPLACES `tag` AS THE APPLICATIONS WORD FOR ASSIGNING KNIVES TO MORE SPECIFIC IDENTIFIERS FOR USAGE SUCH AS FILTERS, GROUPING BY. `tag` WILL STILL BE ACCEPTED, BUT IT IS AN ALIAS FOR QOL.
  - IDENTIFIED AS A GROUP OR FIELD THAT IS/ARE RELATED, UTILIZES `Section Line Indicators`(`SLI`) made up of thirtyone dashes `-`
  - There is ALWAYS a SLI above and below a `SectionID`.
  - THE FILE TITLE(FIRST HEADER) WILL ALWAYS BE A MARKDOWN TITLE HASH `#`, IT IS ONLY UTILIZED FOR THE TOP OF THE FILE; ALL OTHER HEADINGS ARE `// SectionID`
  - THERE IS NEVER AN EMPTY LINE ABOVE A `SectionID`.
  - THERE IS ALWAYS AN EMPTY LINE AFTER A `SectionID`
    - THERE IS ALWAYS A `SLI` AFTER THE EMPTY LINE TO CLOSE OUT THE `SectionID` HEADING.
    - `SLI` WILL ALLOW US TO ADD DATA REFERENCES DIRECTLY INTO THOSE SECTIONS. For example, we can identify a group as "affordable" tag, or "luxury" tag, right into the section. THE DISTINCT usage of the lines indicate to the parser that this is a section, and it should find and assign the tag when adding the knives to the database.
- `new`: a core feature and option flag
  - It will represent recently added knives to the database. The `new` as a command(to set its cache generation) and a `-flag` option. Example;
    - `knivves list -new`: will list all of the knife that are tagged *NEW*.
    - `knivves new -oneg`: will set new to tag only the last updated models to the database with command `knivves update`
  - It will be represented in textual as a menu option for filtering and as a tag in the lists.
  - It will operate under a `three-generation-cache` rule, meaning it will have the option to keep recently added knife models BY UP TO THREE DATABASE UPDATES (knivves update). By default, whenever a new knife is added to the database, it will show only one generation of recently added.
- "BuyList":"The buy list window should be clearly displayed on the vault and or list page. It is a priority list for the next aquisitions to my collection, they will be titled in the markdown ingestion file as a `section` with the title `BuyList`"

> [REF1]
> POSSIBLE PARSING COMPLICATION REFERENCE TRANSLATION [FOR AGENT TO DECIDE IF NECESSARY]
> "Knife ID and (BG41H)" MIGHT BENEFIT FROM PRE-PROCESSING IT, PARSING IT TO "Knife ID - BG41H" IN THE INGESTION MARKDOWN FILE. IT MAY NOT BE NECESSARY. I AM NOT SURE. THIS IS PRECAUTIONARY NOTE ONLY.
>
> [REF2]
> MARKDOWN INGESTION LINKS FILE, FORMAT EXAMPLE

```markdown
# KNIFE ADDITIONS

-------------------------------
// ForCamping

-------------------------------

- [DreamTech Flipper Folding Knife, D2 Satin, Titanium Grey, D4285TG](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Folding-Knife-D2-Satin-Titanium-Grey-D4285TG)
- [DreamTech Flipper Crossbar Lock Folding Knife, VG-10, Titanium Grey, D4032TG](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Crossbar-Lock-Folding-Knife-VG-10-Titanium-Grey-D4032TG)
- [Bestech Toddler G10 Beige (BG64C)](https://houseofknives.ca/toddler-g10-beige-bt25034/)
- [Bestech Ququ Satin 14C28N G10 Black (BG57A-1)](https://houseofknives.ca/bestech-ququ-satin-14c28n-g10-black-bg57a-1/)
- [Vosteed Porcupine Folding Knife, 14C28N Black SW, Micarta Black, A2601](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Porcupine-Folding-Knife-14C28N-Black-SW-Micarta-Black-A2601)
- [Bestech Swordfish Satin 14C28N G10 Black/White - BG62B](https://houseofknives.ca/bestech-swordfish-satin-14c28n-g10-black-white-bg62b/)
- [Bestech Swordfish Stonewashed 14C28N G10 Black/Blue - BG62F](https://houseofknives.ca/bestech-swordfish-stonewashed-14c28n-g10-black-blue-bg62f/)
- [Bestechman Sprite B-Lock Folding Knife, M390 Dark Bead Blast SW, Titanium Dark Bead Blast SW, BMK21D](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Sprite-B-Lock-Folding-Knife-M390-Dark-Bead-Blast-SW-Titanium-Dark-Bead-Blast-SW-BMK21D)

-------------------------------

```

- `//` indicates a `SectionID` Line
- `ForCamping` IS THE `SectionID` NOT A REAL SECTION, ONLY AN EXAMPLE. IT IS NOT TO BE ADDED INTO THE CLI. IT IS FOR CONTEXT AND LEARNING.

-------------------------------
// BUY LIST DESCENDING PRIORITY

-------------------------------

> This list IS in numerical order, DESCENDING by most sought after at the top.

- [DreamTech Flipper Folding Knife, D2 Satin, Titanium Grey, D4285TG](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Folding-Knife-D2-Satin-Titanium-Grey-D4285TG)
- [DreamTech Flipper Crossbar Lock Folding Knife, VG-10, Titanium Grey, D4032TG](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Crossbar-Lock-Folding-Knife-VG-10-Titanium-Grey-D4032TG)
- [Bestech Toddler G10 Beige (BG64C)](https://houseofknives.ca/toddler-g10-beige-bt25034/)
- [Bestech Ququ Satin 14C28N G10 Black (BG57A-1)](https://houseofknives.ca/bestech-ququ-satin-14c28n-g10-black-bg57a-1/)
- [Vosteed Porcupine Folding Knife, 14C28N Black SW, Micarta Black, A2601](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Porcupine-Folding-Knife-14C28N-Black-SW-Micarta-Black-A2601)
- [Bestech Swordfish Satin 14C28N G10 Black/White - BG62B](https://houseofknives.ca/bestech-swordfish-satin-14c28n-g10-black-white-bg62b/)
- [Bestech Swordfish Stonewashed 14C28N G10 Black/Blue - BG62F](https://houseofknives.ca/bestech-swordfish-stonewashed-14c28n-g10-black-blue-bg62f/)
- [Bestechman Sprite B-Lock Folding Knife, M390 Dark Bead Blast SW, Titanium Dark Bead Blast SW, BMK21D](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Sprite-B-Lock-Folding-Knife-M390-Dark-Bead-Blast-SW-Titanium-Dark-Bead-Blast-SW-BMK21D)
- [Bestechman Lanza Flipper Folding Knife, Damascus, Olive Wood, BMK14-D-4](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Lanza-Flipper-Folding-Knife-Damascus-Olive-Wood-BMK14-D-4)
- [Bestechman Flick Flipper Folding Knife, D2 Satin, G10 Light Blue, BMK13D](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Flick-Flipper-Folding-Knife-D2-Satin-G10-Light-Blue-BMK13D)
- [Bestchman Velix Flipper Button Lock Folding Knife, 14C28N Gold PVD, G10 OD Green, BMK07G](https://www.bladescanada.com/Bestechman-Knives/Bestchman-Velix-Flipper-Button-Lock-Folding-Knife-14C28N-Gold-PVD-G10-OD-Green-BMK07G)
- [Gerber Sharkbelly Lockback Folding Knife, 420HC Satin, GRN Black Sharkskin Grip, G3214](https://www.bladescanada.com/Gerber-Gear-Knives/Gerber-Sharkbelly-Lockback-Folding-Knife-420HC-Satin-GRN-Black-Sharkskin-Grip-G3214)
- [Vixino Knives Rockshark Crossbar Lock Folding Knife, 14C28N Black SW, G10 White Textured, VX501G1](https://www.bladescanada.com/All-Folding-Knives/Vixino-Knives-Rockshark-Crossbar-Lock-Folding-Knife-14C28N-Black-SW-G10-White-Textured-VX501G1)
- [Falcon Flipper Folding Knife, Assisted Opening, 440 Stainless Satin, Aluminum Grey, KS2110GY](https://www.bladescanada.com/All-Folding-Knives/Falcon-Flipper-Folding-Knife-Assisted-Opening-440-Stainless-Satin-Aluminum-Grey-KS2110GY)
- [DreamTech Button Lock Folding Knife, D2 Bead Blast, Micarta Black/Red, D4542MR](https://www.bladescanada.com/DreamTech/DreamTech-Button-Lock-Folding-Knife-D2-Bead-Blast-Micarta-Black-Red-D4542MR)
- [DreamTech Button Lock Folding Knife, D2 Bead Blast, Micarta Blue/Green, D4542MBL](https://www.bladescanada.com/DreamTech/DreamTech-Button-Lock-Folding-Knife-D2-Bead-Blast-Micarta-Blue-Green-D4542MBL)
- [DreamTech Button Lock Folding KNife, D2 Bead Blast, G10 Black, D4542GB](https://www.bladescanada.com/DreamTech/DreamTech-Button-Lock-Folding-KNife-D2-Bead-Blast-G10-Black-D4542GB)
- [Bestechman Cicada's Wing B-Lock Folding Knife, 10Cr15MoV Pink, Ultem Jade , BMK06H](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Cicadas-Wing-B-Lock-Folding-Knife-10Cr15MoV-Pink-Ultem-Jade-BMK06H)
- [Bestechman Cicada's Wing B-Lock Folding Knife, 10Cr15MoV Gold, Ultem, BMK06D](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Cicadas-Wing-B-Lock-Folding-Knife-10Cr15MoV-Gold-Ultem-BMK06D)
- [Bestech Noctar Bar Lock Folding Knife, 14C28N Satin, G10 Khaki, BG66C](https://www.bladescanada.com/Bestech-Knives/Bestech-Noctar-Bar-Lock-Folding-Knife-14C28N-Satin-G10-Khaki-BG66C)
- [Bestech Noctar Bar Lock Folding Knife, 14C28N Satin, G10 Black, BG66A](https://www.bladescanada.com/Bestech-Knives/Bestech-Noctar-Bar-Lock-Folding-Knife-14C28N-Satin-G10-Black-BG66A)
- [Bestech Noctar Bar Lock Folding Knife, 14C28N Black SW, G10 Black, BG66H](https://www.bladescanada.com/Bestech-Knives/Bestech-Noctar-Bar-Lock-Folding-Knife-14C28N-Black-SW-G10-Black-BG66H)
- [https://www.bladescanada.com/Bestech-Knives/Bestech-Duoz-Flipper-Folding-Knife-14C28N-Gold-PVD-G10-OD-Green-BG65F](Bestech Duoz Flipper Folding Knife, 14C28N Gold PVD, G10 OD Green, BG65F)
- [DreamTech Flipper Button Lock Knife, 14C28N Bead Blast, G10 Black, D4052GB](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Button-Lock-Knife-14C28N-Bead-Blast-G10-Black-D4052GB)
- [Molsect Croc Flipper Button Lock Folding Knife, 14C28N Satin, G10 Black Textured, M1216B](https://www.bladescanada.com/Molsect-Knives/Molsect-Croc-Flipper-Button-Lock-Folding-Knife-14C28N-Satin-G10-Black-Textured-M1216B)
- [Honey Badger Large Flipper Folding Knife, D2 Satin, Nylon Textured Tan, HB1010](https://www.bladescanada.com/Honey-Badger-Knives/Honey-Badger-Large-Flipper-Folding-Knife-D2-Satin-Nylon-Textured-Tan-HB1010)
// Canadian Tire *NewSource*, *AffordableSource*
- [Kershaw Skyline Folding Knife#175-2469-8](https://www.canadiantire.ca/en/pdp/kershaw-skyline-folding-knife-1752469p.html)

-------------------------------
// MAIN SOURCES

-------------------------------

- [KershawCanada](https://kershawcanada.com/)
- [BladesCanada](https://www.bladescanada.com/)
- [HouseOfKnives](https://houseofknives.ca/)
- [CanadianTire](https://www.canadiantire.ca/en/cat/sports-recreation/hunting/hunting-knives/pocket-knives-DC0002384.html)

-------------------------------
// NEW SOURCES

-------------------------------

- [KershawCanada](https://kershawcanada.com/)
- [CanadianTire](https://www.canadiantire.ca/en/cat/sports-recreation/hunting/hunting-knives/pocket-knives-DC0002384.html)

-------------------------------
// UNSORTED

-------------------------------

- [Vosteed Psyop Button Lock Flipper Folding Knife, Elmax Satin, Titanium Grey Curved, A2204](<https://www.bladescanada.c>
om/Vosteed-Knives/Vosteed-Psyop-Button-Lock-Flipper-Folding-Knife-Elmax-Satin-Titanium-Grey-Curved-A2204)
- [Kunwu Gringo Verta Titanium Honeydew (B712T-R2-1)](https://houseofknives.ca/kunwu-gringo-verta-titanium-honeydew-b712t-r2-1/?srsltid=AfmBOoo72H_0fG5M6TChLD1obmB1HUzFAsm8OsWTE8trPFhIHBO2XSaL)
- [Microtech M-Stitch Ram-Lok Folding Knife, M390 SW, Aluminum Tan Frag, 169MRL-10FRTA](https://www.bladescanada.com/Microtech-Knives/Microtech-M-Stitch-Ram-Lok-Folding-Knife-M390-SW-Aluminum-Tan-Frag-169MRL-10FRTA)
- [Microtech MSI Mini Ram-Lok Folding Knife, M390MK Two-Tone, Aluminum Grey Fluted, 210M-1FLNC](https://www.bladescanada.com/index.php?main_page=knife_fold_info&cPath=118&products_id=54388)
- [Microtech MSI Mini Ram-Lok Folding Knife, M390MK SW, Aluminum OD Green Fluted, 210M-10FLOD](https://www.bladescanada.com/Microtech-Knives/Microtech-MSI-Mini-Ram-Lok-Folding-Knife-M390MK-SW-Aluminum-OD-Green-Fluted-210M-10FLOD)
- [CIVIVI Buster FG Superlock Folding Knife, Nitro-V Black SW, G10 Black/Golden, C24052-1](https://www.bladescanada.com/CIVIVI-Knives/Civivi-Buster-FG-Superlock-Folding-Knife-Nitro-V-Black-SW-G10-Black-Golden-C24052-1)
- [CIVIVI Buster FG Superlock Folding Knife, Nitro-V Black SW, Micarta Green, C24052-3](https://www.bladescanada.com/CIVIVI-Knives/Civivi-Buster-FG-Superlock-Folding-Knife-Nitro-V-Black-SW-Micarta-Green-C24052-3)
- [Trivisa Batwing Crossbar Lock Folding Knife, 14C28N Rose Gold, G10 Black/Carbon Fiber, JM10L-CG-14](https://www.bladescanada.com/Trivisa-Knives/Trivisa-Batwing-Crossbar-Lock-Folding-Knife-14C28N-Rose-Gold-G10-Black-Carbon-Fiber-JM10L-CG-14)
- [Trivisa Batwing Crossbar Lock Folding Knife, 14C28N Black, Micarta Black, JM10S-BM-14](https://www.bladescanada.com/Trivisa-Knives/Trivisa-Batwing-Crossbar-Lock-Folding-Knife-14C28N-Black-Micarta-Black-JM10S-BM-14)
- [Trivisa Batwing Crossbar Lock Folding Knife, 14C28N SW, G10 Black, JM10S-BG-14]<https://www.bladescanada.com/Trivisa-Knives/Trivisa-Batwing-Crossbar-Lock-Folding-Knife-14C28N-SW-G10-Black-JM10S-BG-14()>
- [Trivisa Batwing Crossbar Lock Folding Knife, 14C28N SW, Micarta Black, JM10L-BM-14](https://www.bladescanada.com/Trivisa-Knives/Trivisa-Batwing-Crossbar-Lock-Folding-Knife-14C28N-SW-Micarta-Black-JM10L-BM-14)
- [WE Knife Flight Line Flipper Folding Knife, Limited Edition, M390 Black SW, Titanium Bronze, WE23089-2](https://www.bladescanada.com/index.php?main_page=knife_fold_info&cPath=428&products_id=54277)
- [WE Knife Flight Line Flipper Folding Knife, Limited Edition, M390 Satin, Titanium Bead Blasted, WE23089-3](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Flight-Line-Flipper-Folding-Knife-Limited-Edition-M390-Satin-Titanium-Bead-Blasted-WE23089-3)
- [WE Knife Flight Line Flipper Folding Knife, Limited Edition, M390 SW, Titanium Dark Grey, WE23089-1](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Flight-Line-Flipper-Folding-Knife-Limited-Edition-M390-SW-Titanium-Dark-Grey-WE24046-3)
- [Rike Knife 1902 Flipper Framelock Knife, M390 Bead Blast/Satin, Titanium Dark Grey/CF Marble Blue & Black, RK1902-BCF](https://www.bladescanada.com/Rike-Knives/Rike-Knife-1902-Flipper-Framelock-Knife-M390-Bead-Blast-Satin-Titanium-Dark-Grey-CF-Marble-Blue-Black-RK1902-BCF)
- [OKC Corporal Crossbar Lock Folding Knife, Stainless SW, G10 Tan, ON9006](https://www.bladescanada.com/Ontario-Knives-OKC/OKC-Corporal-Crossbar-Lock-Folding-Knife-Stainless-SW-G10-Tan-ON9006)
- [Knafs Lander 5 Framelock Folding Knife, Black Stonewash Blade, Cold Forged Steel Topo, 00684](https://www.bladescanada.com/Knafs-Knives/Knafs-Lander-5-Frame-Lock-Folding-Knife-Black-Stonewash-Blade-Cold-Forged-Steel-Topo-00684)
- [SRM Knives Palfrey Framelock Folding Knife, 14C28N Bead Blast, G10 Ivory, 135L-GT](https://www.bladescanada.com/SRM-Knives/SRM-Knives-Palfrey-Framelock-Folding-Knife-14C28N-Bead-Blast-G10-Ivory-135L-GT)
- [Kizer Little Ringbo Button Lock Folding Knife, AEB-L Satin, Aluminum Silver, V3708A1](https://www.bladescanada.com/Kizer-Knives/Kizer-Little-Ringbo-Button-Lock-Folding-Knife-AEB-L-Satin-Aluminum-Silver-V3708A1)
- [CIVIVI Iron Tide Flipper Button Lock Folding Knife, 14C28N Grey SW, Aluminum Grey, C25011-3](https://www.bladescanada.com/CIVIVI-Knives/CIVIVI-Iron-Tide-Flipper-Button-Lock-Folding-Knife-14C28N-Grey-SW-Aluminum-Grey-C25011-3)
- [SENCUT Vyrce Flipper Folding Knife, D2 Satin, Micarta Purple, S25104-3](https://www.bladescanada.com/SENCUT-Knives/SENCUT-Vyrce-Flipper-Folding-Knife-D2-Satin-Micarta-Purple-S25104-3)
- [Bestech VK-KUZE Titanium Dark Bead Blast/Stonewash (BT2504B)](https://houseofknives.ca/vk-kuze-ti-dark-bead-blast-stonewash-bt25039/)
- [Bestech Mothus G10 Dark Blue - BG67F](https://houseofknives.ca/bestech-mothus-g10-dark-blue-bg67f/)
- [Bestech Mothus G10 Beige - BG67B](https://houseofknives.ca/bestech-mothus-g10-beige-bg67b/)
- [Gerber Ripstop II Stainless Steel Fine Edge Folding Pocket Knife, 7.4-in](https://www.canadiantire.ca/en/pdp/gerber-ripstop-ii-stainless-steel-fine-edge-folding-pocket-knife-7-4-in-3750210p.html?rq=FOLDING+KNIFE)
- [SOG Fielder Folding Knife with Wood Handle, 3.3-in](https://www.canadiantire.ca/en/pdp/sog-fielder-folding-knife-with-wood-handle-3-3-in-0755603p.html?rq=FOLDING+KNIFE)
- [Bestech VK-KUZE Titanium Dark Bead Blast/Stonewash - BT2504B](https://houseofknives.ca/vk-kuze-ti-dark-bead-blast-stonewash-bt25039/)
- [Bestech Wet Nellie Titanium Timascus - BT2505E](https://houseofknives.ca/bestech-wet-nellie-titanium-timascus-bt2505e/)
- [Bestech Seraph Black Stonewashed M390 Ti Black/Bronze - BT2403E](https://houseofknives.ca/bestech-seraph-black-stonewashed-m390-ti-black-bronze-bt2403e/)
- [Bestech Razon Black Magnacut Ti White - BT2406C](https://houseofknives.ca/bestech-razon-black-magnacut-ti-white-bt2406c/)
- [Bestechman Sprite Titanium Bronze - BMK21B](https://houseofknives.ca/bestechman-sprite-titanium-bronze-bmk21b/)
- [Bestechman Sprite Titanium - BMK21A](https://houseofknives.ca/bestechman-sprite-titanium-bmk21a/)
- [Bestechman Sprite Titanium Dark Bead Blast Stonewash - BMK21D](https://houseofknives.ca/bestechman-sprite-titanium-dark-bead-blast-stonewash-bmk21d/)
- [Bestechman Vector Aluminum Grey - BMK15B](https://houseofknives.ca/bestechman-vector-aluminum-grey-bmk15b/)
- [Bestech VK-KUZE Titanium Black Stonewash - BT2504C](https://houseofknives.ca/vk-kuze-ti-blk-stonewash-bt25040/)
- [Bestech Wet Nellie Titanium - BT2505B](https://houseofknives.ca/bestech-wet-nellie-titanium-bt2505b/)
- [Bestech Wet Nellie Titanium Bead Blasted DLC - BT2505G](https://houseofknives.ca/bestech-wet-nellie-titanium-bead-blasted-dlc-bt2505g/)
- [Bestech Mini Taipan Titanium Black PVD Left Handed - BT2603E-L](https://houseofknives.ca/bestech-mini-taipan-titanium-black-pvd-left-handed-bt2603e-l/)
- [Bestech Razon Black Magnacut Ti White - BT2406C](https://houseofknives.ca/bestech-razon-black-magnacut-ti-white-bt2406c/)
- [Bestech Mini Taipan Titanium Bronze - BT2603B](https://houseofknives.ca/bestech-mini-taipan-titanium-bronze-bt2603b/)
- [Bestech Mini Taipan Titanium Black PVD - BT2603E](https://houseofknives.ca/bestech-mini-taipan-titanium-black-pvd-bt2603e/)
- [WE Knife Hull Flipper Folding Knife, Limited Edition, M390 Grey SW, Titanium Grey, WE24046-2](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Hull-Flipper-Folding-Knife-Limited-Edition-M390-Grey-SW-Titanium-Grey-WE24046-2)
- [WE Knife Breach Flipper Framelock Knife, Limited Edition, M390 Black Brushed, Titanium Black, WE25077-2](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Breach-Flipper-Framelock-Knife-Limited-Edition-M390-Black-Brushed-Titanium-Black-WE25077-2)
- [WE Knife Breach Flipper Framelock Knife, Limited Edition, M390 Dark Grey SW, Titanium Charcoal Grey, WE25077-1](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Breach-Flipper-Framelock-Knife-Limited-Edition-M390-Dark-Grey-SW-Titanium-Charcoal-Grey-WE25077-1)
- [WE Knife Hull Flipper Folding Knife, Limited Edition, M390 Satin, Titanium Black, WE24046-1](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Hull-Flipper-Folding-Knife-Limited-Edition-M390-Satin-Titanium-Black-WE24046-1)
- [CIVIVI Iron Tide Flipper Button Lock Folding Knife, 14C28N Grey SW, Aluminum Grey, C25011-3](https://www.bladescanada.com/CIVIVI-Knives/CIVIVI-Iron-Tide-Flipper-Button-Lock-Folding-Knife-14C28N-Grey-SW-Aluminum-Grey-C25011-3)
- [SENCUT Vyrce Flipper Folding Knife, D2 Satin, Micarta Purple, S25104-3](https://www.bladescanada.com/SENCUT-Knives/SENCUT-Vyrce-Flipper-Folding-Knife-D2-Satin-Micarta-Purple-S25104-3)
- [WE Knife Reveille Framelock Folding Knife, Limited Edition, M390 Two-Tone, Titanium Olive Grey, WE23057-2](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Reveille-Framelock-Folding-Knife-Limited-Edition-M390-Two-Tone-Titanium-Olive-Grey-WE23057-2)
- [WE Knife Reveille Framelock Folding Knife, Limited Edition, M390 Two-Tone, Titanium Bronze, WE23089-3](https://www.bladescanada.com/WE-Knife-Co.-Knives/WE-Knife-Reveille-Framelock-Folding-Knife-Limited-Edition-M390-Two-Tone-Titanium-Bronze-WE23089-3)
- [https://www.bladescanada.com/Kizer-Knives/Kizer-Microbe-Button-Lock-Folding-Knife-14C28N-Grey-Stonewash-Micarta-Vortex-V2742A5](Kizer Microbe Button Lock Folding Knife, 14C28N Grey Stonewash, Micarta Vortex, V2742A5)
- [Kizer Microbe Button Folding Knife, 14C28N, Micarta Norplex UltreX, V2742A2](https://www.bladescanada.com/Kizer-Knives/Kizer-Microbe-Button-Folding-Knife-14C28N-Micarta-Norplex-UltreX-V2742A2)
- [Kizer Microbe Button Lock Folding Knife, M390 Matt Black, Fat Carbon Fiber, KI2742A2](https://www.bladescanada.com/Kizer-Knives/Kizer-Microbe-Button-Lock-Folding-Knife-M390-Matt-Black-Fat-Carbon-Fiber-KI2742A2)
- [SENCUT Vyrce Flipper Folding Knife, D2 Satin, Micarta Purple, S25104-3](https://www.bladescanada.com/SENCUT-Knives/SENCUT-Vyrce-Flipper-Folding-Knife-D2-Satin-Micarta-Purple-S25104-3)
- [Petrified Fish Zonda Folding Knife, 14C28N Black SW, G10 Black, PFB06DDW](https://www.bladescanada.com/Petrified-Fish-Knives/Petrified-Fish-Zonda-Folding-Knife-14C28N-Black-SW-G10-Black-PFB06DDW)
- [Bestech Cobber Crossbar Lock Folding Knife, 14C28N Black, Micarta Brown, BG68F](https://www.bladescanada.com/Bestech-Knives/Bestech-Cobber-Crossbar-Lock-Folding-Knife-14C28N-Black-Micarta-Brown-BG68F)
- [Bestech Constellation Flipper Framelock Knife, M-Cut Black, Titanium/Fat CF Dark Matter Gold, BT2501C](https://www.bladescanada.com/Bestech-Knives/Bestech-Constellation-Flipper-Framelock-Knife-M-Cut-Black-Titanium-Fat-CF-Dark-Matter-Gold-BT2501C)
- [DreamTech Pivot Button Lock Folding Knife, M390 Satin, Titanium Purple Frag, D4129TP](https://www.bladescanada.com/DreamTech/DreamTech-Pivot-Button-Lock-Folding-Knife-M390-Satin-Titanium-Purple-Frag-D4129TP)
- [Bestchman Velix Flipper Button Lock Folding Knife, 14C28N Two-Tone, G10 Black, BMK07A](https://www.bladescanada.com/Bestechman-Knives/Bestchman-Velix-Flipper-Button-Lock-Folding-Knife-14C28N-Two-Tone-G10-Black-BMK07A)
- [Microtech MSI Mini Ram-Lok Folding Knife, M390MK Cerakote Sniper Gray, Aluminum Black Frag, 210M-1FRCSG-Z13](https://www.bladescanada.com/Microtech-Knives/Microtech-MSI-Mini-Ram-Lok-Folding-Knife-M390MK-Cerakote-Sniper-Gray-Aluminum-Black-Frag-210M-1FRCSG-Z13)
- [Cold Steel Engage Folding Knife, S35VN 3", G10 Black, FL-30DPLC-35](https://www.bladescanada.com/Cold-Steel-Knives/Cold-Steel-Engage-Folding-Knife-S35VN-3-G10-Black-FL-30DPLC-35)
- [Trivisa Skarn Crossbar Lock Folding Knife, M390 Satin, Titanium Silver, JM11-W-M](https://www.bladescanada.com/Trivisa-Knives/Trivisa-Skarn-Crossbar-Lock-Folding-Knife-M390-Satin-Titanium-Silver-JM11-W-M)
- [Trivisa Skarn Crossbar Lock Folding Knife, M390 Rose Gold, Titanium Rose Gold, JM11-RG-M](https://www.bladescanada.com/Trivisa-Knives/Trivisa-Skarn-Crossbar-Lock-Folding-Knife-M390-Rose-Gold-Titanium-Rose-Gold-JM11-RG-M)
- [Microtech Socom Delta RAM-LOK S/E Folding Knife, M390 SW, Aluminum OD Green, 159RL-10OD](https://www.bladescanada.com/Microtech-Knives/Microtech-Socom-Delta-RAM-LOK-S-E-Folding-Knife-M390-SW-Aluminum-OD-Green-159RL-10OD)
- [Microtech Socom Delta RAM-LOK Folding Knife, M390 SW, Alumium Tan, 159RL-10TA](https://www.bladescanada.com/Microtech-Knives/Microtech-Socom-Delta-RAM-LOK-Folding-Knife-M390-SW-Alumium-Tan-159RL-10TA)
- [Kunwu Diablo Framelock Folding Knife, Vanax Black, Titanium Grey Orange Peel, K717T-2R](https://www.bladescanada.com/Kunwu-Knives/Kunwu-Diablo-Framelock-Folding-Knife-Vanax-Black-Titanium-Grey-Orange-Peel-K717T-2R)
- [Kunwu Poon Padre Framelock Folding Knife, S90V Black, Titanium Grey Orange Peel, K706TO-T2R](https://www.bladescanada.com/Kunwu-Knives/Kunwu-Poon-Padre-Framelock-Folding-Knife-S90V-Black-Titanium-Grey-Orange-Peel-K706TO-T2R)
- [Kunwu Poon Padre Framelock Folding Knife, S90V Satin, Titanium Grey Orange Peel, K706TO-T2A](https://www.bladescanada.com/Kunwu-Knives/Kunwu-Poon-Padre-Framelock-Folding-Knife-S90V-Satin-Titanium-Grey-Orange-Peel-K706TO-T2A)
- [Hogue Deka ABLE Lock Folding Knife, CPM MagnaCut Tumbled Finish, Polymer Black, HO24379](https://www.bladescanada.com/Hogue-Knives/Hogue-Deka-ABLE-Lock-Folding-Knife-CPM-MagnaCut-Tumbled-Finish-Polymer-Black-HO24379)
- [Hogue Mysto ABLE Lock Folding Knife, CPM MagnaCut Black SW, Richlite Browns Point, HO24453](https://www.bladescanada.com/Hogue-Knives/Hogue-Mysto-ABLE-Lock-Folding-Knife-CPM-MagnaCut-Black-SW-Richlite-Browns-Point-HO24453)
- [DreamTech Flipper Folding Knife, D2 Satin, Titanium Blue, D4285TBL](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Folding-Knife-D2-Satin-Titanium-Blue-D4285TBL)
- [DreamTech Flipper Crossbar Lock Folding Knife, VG-10 Black, Titanium Black, D4032TB](https://www.bladescanada.com/DreamTech/DreamTech-Flipper-Crossbar-Lock-Folding-Knife-VG-10-Black-Titanium-Black-D4032TB)
- [Vosteed Raccoon TiSlim Crossbar Lock Folding Knife, S35VN Acid Wash & Stonewash, Titanium Acid Wash Copper, A4508](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Raccoon-TiSlim-Crossbar-Lock-Folding-Knife-S35VN-Acid-Wash-Stonewash-Titanium-Acid-Wash-Copper-A4508)
- [Vosteed Zander Flipper Vanchor Lock Folding Knife, S35VN Satin, Aluminum Gray, A4605](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Zander-Flipper-Vanchor-Lock-Folding-Knife-S35VN-Satin-Aluminum-Gray-A4605)
- [Vosteed Zander Flipper Vanchor Lock Folding Knife, S35VN Copper Dune, Aluminum Olive Green, A4604](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Zander-Flipper-Vanchor-Lock-Folding-Knife-S35VN-Copper-Dune-Aluminum-Olive-Green-A4604)
- [Vosteed Zander Flipper Vanchor Lock Folding Knife, S35VN Stonewash, Aluminum Olive Green, A4602](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Zander-Flipper-Vanchor-Lock-Folding-Knife-S35VN-Stonewash-Aluminum-Olive-Green-A4602)
- [Vosteed Zander Flipper Vanchor Lock Folding Knife, S35VN Copper Dune, Aluminum Black, A4601](https://www.bladescanada.com/Vosteed-Knives/Vosteed-Zander-Flipper-Vanchor-Lock-Folding-Knife-S35VN-Copper-Dune-Aluminum-Black-A4601)

-------------------------------
// UNSORTED

-------------------------------

- [TODO:GET-KNIFE-DATA](https://www.bladescanada.com/Bestech-Knives/Bestech-Cobber-Crossbar-Lock-Folding-Knife-14C28N-Satin-SW-G10-Black-BG68A)
- [TODO:GET-KNIFE-DATA](https://www.bladescanada.com/Bestech-Knives/Bestech-Mothus-Crossbar-Lock-Folding-Knife-14C28N-Black-G10-Black-BG67G)
- [TODO:GET-KNIFE-DATA](https://www.bladescanada.com/Bestech-Knives/Bestech-Wet-Nelly-Flipper-Button-Lock-Knife-MagnaCut-Grey-Titanium-Grey-Bronze-SW-BT2505D)
- [TODO:GET-KNIFE-DATA](https://www.bladescanada.com/Bestech-Knives/Bestech-Taipan-Framelock-Folding-Knife-MagnaCut-Satin-Titanium-Grey-BT2503C)
- [TODO:GET-KNIFE-DATA](https://www.bladescanada.com/Bestechman-Knives/Bestechman-Sprite-B-Lock-Folding-Knife-M390-SW-Saitn-Titanium-Crystallized-Blue-BMK21G)

-------------------------------
