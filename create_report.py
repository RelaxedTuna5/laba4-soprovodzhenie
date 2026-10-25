import os
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_report():
    doc = docx.Document()

    # --- Page setup (A4, 2 cm margins, left 2.5 cm) ---
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    section.different_first_page_header_footer = True

    # Footer page number (starting from page 2)
    footer = section.footer
    f_p = footer.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fldSimple = OxmlElement('w:fldSimple')
    fldSimple.set(qn('w:instr'), 'PAGE')
    f_p._p.append(fldSimple)

    # Base style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(14)
    style_normal.font.color.rgb = RGBColor(0, 0, 0)
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(0)
    style_normal.paragraph_format.space_before = Pt(0)

    def p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, size=14, indent=True, space_before=0, space_after=0):
        par = doc.add_paragraph()
        par.alignment = align
        fmt = par.paragraph_format
        fmt.space_before = Pt(space_before)
        fmt.space_after = Pt(space_after)
        fmt.line_spacing = 1.15
        if indent:
            fmt.first_line_indent = Cm(1.25)
        else:
            fmt.first_line_indent = Cm(0)
        
        if text:
            run = par.add_run(text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor(0, 0, 0)
            run.bold = bold
            run.italic = italic
        return par

    def heading(text, level=2):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt = par.paragraph_format
        fmt.space_before = Pt(12)
        fmt.space_after = Pt(6)
        fmt.first_line_indent = Cm(0)
        fmt.keep_with_next = True
        run = par.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
        run.bold = True
        return par

    def add_image(img_path, caption_text, width_cm=15.0):
        if os.path.exists(img_path):
            img_p = doc.add_paragraph()
            img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            img_p.paragraph_format.space_before = Pt(8)
            img_p.paragraph_format.space_after = Pt(4)
            img_p.paragraph_format.first_line_indent = Cm(0)
            img_p.paragraph_format.keep_with_next = True
            run = img_p.add_run()
            run.add_picture(img_path, width=Cm(width_cm))
        else:
            p(f"[Изображение {img_path} не найдено]", align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, indent=False)

        cap_p = doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.space_before = Pt(2)
        cap_p.paragraph_format.space_after = Pt(8)
        cap_p.paragraph_format.first_line_indent = Cm(0)
        r = cap_p.add_run(caption_text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0, 0, 0)

    # ==================== ТИТУЛЬНЫЙ ЛИСТ ====================
    p("САНКТ-ПЕТЕРБУРГСКИЙ ПОЛИТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("ПЕТРА ВЕЛИКОГО", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("", indent=False)
    p("Институт компьютерных наук и кибербезопасности", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("Высшая школа программной инженерии", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("", indent=False)
    p("", indent=False)
    p("", indent=False)
    p("Отчет по лабораторной работе №4", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, indent=False, size=16)
    p("«Программное средство для аналитики задач»", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, indent=False, size=14)
    p("по дисциплине «Внедрение и сопровождение программного продукта»", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("", indent=False)
    p("", indent=False)
    p("", indent=False)

    # Блок исполнителя и преподавателей
    table = doc.add_table(rows=5, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Убираем границы
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="none"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

    row_data = [
        ("Выполнил студент:", ""),
        ("гр. 5140904/60401", "______________________ Суханов С.С."),
        ("", "(подпись)"),
        ("Преподаватели:", ""),
        ("доцент, к.т.н.", "______________________ Никифоров И.В."),
    ]
    # Настроим строки таблицы
    t_rows = table.rows
    t_rows[0].cells[0].paragraphs[0].text = "Выполнил студент:"
    t_rows[0].cells[1].paragraphs[0].text = ""
    
    t_rows[1].cells[0].paragraphs[0].text = "гр. 5140904/60401"
    t_rows[1].cells[1].paragraphs[0].text = "______________________ Суханов С.С."
    
    t_rows[2].cells[0].paragraphs[0].text = ""
    t_rows[2].cells[1].paragraphs[0].text = "         (подпись)"
    
    t_rows[3].cells[0].paragraphs[0].text = "Преподаватели:"
    t_rows[3].cells[1].paragraphs[0].text = "______________________ Никифоров И.В."
    
    t_rows[4].cells[0].paragraphs[0].text = "доцент, к.т.н. Никифоров И.В."
    t_rows[4].cells[0].paragraphs[0].text = ""
    t_rows[4].cells[1].paragraphs[0].text = "______________________ Шишкина В.И."

    for row in table.rows:
        for cell in row.cells:
            for pr in cell.paragraphs:
                pr.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pr.paragraph_format.first_line_indent = Cm(0)
                pr.paragraph_format.space_before = Pt(0)
                pr.paragraph_format.space_after = Pt(2)
                pr.paragraph_format.line_spacing = 1.15
                for r in pr.runs:
                    r.font.name = 'Times New Roman'
                    r.font.size = Pt(13)

    p("", indent=False)
    p("«___» ______________ 2026 г.", align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False, size=14)
    p("", indent=False)
    p("", indent=False)
    p("Санкт-Петербург", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)
    p("2026", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=14)

    # Разрыв страницы после титульного листа
    doc.add_page_break()

    # ==================== РАЗДЕЛ: ЦЕЛЬ ====================
    heading("Цель")
    p("Целью данного задания было получение знаний и практического опыта в работе с REST API систем трекинга задач, а также разработка аналитических инструментов для визуализации данных о задачах в проекте.")

    # ==================== РАЗДЕЛ: РЕШЕНИЕ ====================
    heading("Решение")
    p("Для выполнения задания было выбрано программное средство на языке Python. В процессе разработки были учтены все требования, указанные в задании:")
    
    par = p("Подключение к JIRA через REST API:", indent=False, bold=True, space_before=4)
    par = p("Установлена библиотека requests для выполнения HTTP-запросов к API JIRA. Реализовано получение данных по задачам с поддержкой пагинации, обработки истории изменений (changelog) и дискового кэширования для оптимизации трафика.", indent=False)
    p("Реализовано логирование работы программы с записью в файл logs/jira_analytics.log и выводом в консоль.", indent=False)

    add_image("results/code_structure.png", "Рисунок 1. Структура программного средства и модули", width_cm=15.5)

    p("Основные модули:", indent=False, bold=True, space_before=6)
    
    modules = [
        ("main.py: ", "Главный файл, отвечающий за запуск программы, интерактивное консольное меню и интерфейс командной строки."),
        ("jira_api.py: ", "Модуль для взаимодействия с REST API JIRA (класс JiraClient), реализующий отправку запросов, пагинацию, обработку сетевых ошибок и кэширование."),
        ("tasks.py: ", "Модуль для вычисления аналитических метрик и построения графиков и диаграмм с помощью matplotlib."),
        ("utils.py: ", "Модуль, отвечающий за логирование, парсинг конфигурации config.ini и дат формата ISO-8601."),
        ("tests/test_tasks.py: ", "Папка с автоматическими тестами (8 интеграционных и модульных тестов, работающих с реальным REST API JIRA)."),
        ("setup.py: ", "Механизм сборки программного средства в дистрибутив (wheel / sdist)."),
        ("config.ini: ", "Конфигурационный файл настроек (URL, таймауты, лимиты выборки, каталоги кэша и логов)."),
        ("run.bat / run.sh: ", "Кроссплатформенные скрипты быстрого запуска программы для Windows и Linux.")
    ]
    for name, desc in modules:
        mp = doc.add_paragraph()
        mp.paragraph_format.first_line_indent = Cm(0.5)
        mp.paragraph_format.space_before = Pt(1)
        mp.paragraph_format.space_after = Pt(2)
        r1 = mp.add_run(name)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(13)
        r1.italic = True
        r1.bold = True
        r2 = mp.add_run(desc)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(13)

    # ==================== РАЗДЕЛ: ВИЗУАЛИЗАЦИЯ ПРОГРАММЫ ====================
    heading("Визуализация программы")
    p('После запуска программы пользователю предлагается ввести название проекта, для которого будут строиться графики, например, "Kafka". Затем программа предлагает выбрать вариант работы с выбранным проектом.')
    p('Если выбрать пункт 2: "Построить диаграммы распределения времени по состояниям", то пользователь будет перенаправлен на следующий этап, где ему предстоит выбрать статус. Доступные статусы:')
    
    statuses = ["Open", "Closed", "Reopened", "Resolved", "Patch Available", "In Progress"]
    for s in statuses:
        sp = doc.add_paragraph()
        sp.paragraph_format.first_line_indent = Cm(1.25)
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(1)
        sr = sp.add_run(f"• {s}")
        sr.font.name = 'Times New Roman'
        sr.font.size = Pt(13)

    p("После выбора статуса программа строит соответствующий график и предлагает выбрать следующее действие:")
    p("Выберите команду:", indent=False, bold=True)
    
    commands = [
        "1. Построить гистограмму времени задач в открытом состоянии",
        "2. Построить диаграммы распределения времени по состояниям",
        "3. Построить график создания и закрытия задач с накопительным итогом",
        "4. Построить график задач для пользователей",
        "5. Построить гистограмму времени выполнения задач",
        "6. Построить график задач по степени серьезности",
        "7. Построить все отчеты сразу (полный пайплайн)",
        "8. Завершить работу"
    ]
    for cmd in commands:
        cp = doc.add_paragraph()
        cp.paragraph_format.first_line_indent = Cm(0.5)
        cp.paragraph_format.space_before = Pt(0)
        cp.paragraph_format.space_after = Pt(1)
        cr = cp.add_run(cmd)
        cr.font.name = 'Times New Roman'
        cr.font.size = Pt(13)

    # ==================== РАЗДЕЛ: ТЕСТИРОВАНИЕ ====================
    heading("Тестирование")
    p("Для проверки правильности работы программного средства использовались фильтры и стандартные визуализации JIRA. Для подтверждения надежности кода разработан комплект из 8 автоматических тестов, напрямую взаимодействующих с JIRA REST API и проверяющих вычисление продолжительности задач, переходы между статусами, расчет накопительного итога, топ пользователей и парсинг залогированного времени на реальных тикетах проектов Kafka и HDFS.")

    add_image("results/terminal_tests.png", "Рисунок 2. Результат тестирования", width_cm=15.5)

    # ==================== РАЗДЕЛ: КОРРЕКТНОСТЬ РАБОТЫ ====================
    heading("Корректность работы")
    p("Программное средство было протестировано, и все функции работают корректно. Построены все 6 требуемых заданием аналитических графиков и диаграмм. Скриншоты с визуализациями и результатами выполнения приведены ниже.")

    # График 1
    add_image("results/kafka/1_open_duration_histogram.png", "Рисунок 3. Гистограмма времени задач в открытом состоянии (проект Apache Kafka)", width_cm=15.0)
    p("На рисунке 3 представлена гистограмма распределения времени (в днях), которое закрытые задачи проекта провели в открытом состоянии от момента заведения до закрытия. Большинство задач закрываются в пределах первых 30–60 дней, при этом наблюдается хвост сложных задач, требовавших более длительной проработки.")

    # График 2
    add_image("results/kafka/2_status_Open_distribution.png", "Рисунок 4. Диаграмма распределения времени по состояниям задач (статус Open, проект Apache Kafka)", width_cm=15.0)
    p("На рисунке 4 показано распределение времени нахождения задач в статусе Open до момента их перевода в работу или закрытия, рассчитанное на основе истории изменений (changelog).")

    # График 3
    add_image("results/kafka/3_daily_dynamics_cumulative.png", "Рисунок 5. График количества заведенных и закрытых задач в день с накопительным итогом (проект Apache Kafka)", width_cm=15.5)
    p("На рисунке 5 отражена динамика заведения и закрытия задач по календарным дням, а также накопительный итог (кумулятивные кривые). Накопительные графики наглядно показывают стабильный рост проекта и сопоставимую скорость закрытия задач относительно их поступления.")

    # График 4
    add_image("results/kafka/4_top_30_users.png", "Рисунок 6. График задач для 30 наиболее активных пользователей (проект Apache Kafka)", width_cm=14.0)
    p("На рисунке 6 приведена горизонтальная столбчатая диаграмма для 30 наиболее активных пользователей проекта, учитывающая задачи, в которых пользователь указан в качестве исполнителя (assignee) или автора (reporter).")

    # График 5
    add_image("results/kafka/5_logged_time_spent_HDFS.png", "Рисунок 7. Гистограмма времени выполнения задач на основе залогированного времени (проект Apache HDFS)", width_cm=15.0)
    p("Для проекта Apache Kafka разработчики не заполняют поле залогированного времени (timespent) в открытом трекере. Программное средство интеллектуально определяет это и выполняет построение графика по контрольному проекту Apache HDFS, где трудозатраты фиксируются разработчиками.")

    # График 6
    add_image("results/kafka/6_priority_distribution.png", "Рисунок 8. График задач по степени серьезности (проект Apache Kafka)", width_cm=15.0)
    p("На рисунке 8 представлено распределение задач по степени серьезности (приоритетам). Основную долю составляют задачи приоритета Major (стандартный уровень), задачи уровня Blocker и Critical имеют контролируемую низкую долю.")

    # ==================== РАЗДЕЛ: ЗАКЛЮЧЕНИЕ ====================
    heading("Заключение")
    p("В ходе выполнения задания были достигнуты поставленные цели, получен практический опыт работы с REST API и выполнены все требования. Программное решение соответствует современным стандартам разработки: присутствует модульная структура кода, обработка исключений, тестирование и комментарии.")
    p("Выполнены все критерии оценки: построены все 6 аналитических графиков, проект размещен в репозитории Git, разработано 8 автоматических модульных тестов, реализован механизм сборки в дистрибутив (setup.py) и подготовлены конфигурационный файл config.ini со скриптами запуска под Windows и Linux.")

    output_path = "Суханов_СС_Отчет_4.docx"
    doc.save(output_path)
    print(f"Report successfully created: {output_path}")

if __name__ == "__main__":
    create_report()
