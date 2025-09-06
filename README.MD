# A Novel System for Automatic Detection of TV Commercial Breaks

![plot](./abstract.jpeg)

Manuscript ID: IEEE LATAM Submission ID: 9985 Authors:

* Nicolas Rondan
* Marcos Juayek 
* Jose Joskowicz
* Rafael Sotelo
* Santiago Quincke 
* Andrés Patrone 
* Maximiliano Aguerre 
* Gastón Gonzalez

Affiliation:
Engineering School
Universidad de Montevideo
Uruguay

## Install
* Use conda to create virtual environment:
    * ` conda create -n tv_commercial_break_detector python=3.12 ` 
* Activate environment:
    * `conda activate tv_commercial_break_detector `
* Install dependecies: 
    * `pip install -r requirements.txt`

## Run tv commercial break detector


* If bumpers are available place them place them in folder `./bumpers` if not automatic discovery of bumpers will be executed and bumpers saved in `./bumpers` folder
* Then run: 
    * ` python tv_ad_detector.py --channel_name <channel_name> --video_file <video_file> `


## Configuration

For different configurations edit `config.py`. The software is configured to work in spanish but could be configured for any other language. Most relevant config variables are: ∏

* `START_WORDS`: words to search in bumpers that signal the start of a commercial break and refer to start synomyms e.g: __start__, __beggining__, __etc...__
* `END_WORDS`: words to search in bumpers that signal the end of a commercial break and refer to end synomyms e.g: __end__, __finnish__, __etc...__
* `PUBLICITARIO_WORDS`:  words to search in bumpers that refer to advertisements e.g: __advertisement__, __commercial__
* `OCR_LANGUAGES` : [easyocr](https://github.com/JaidedAI/EasyOCR) codes for ocr languages
* `SPELLCHECKER_LANGUAGE` : spellchecker language configuration
