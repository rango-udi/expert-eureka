"""Export customer business cases as Excel, with optional design media and trace evidence.

The reporting container has no Django or Browser dependency. Imported Robot
results annotate traceability only; newly authored business cases stay unrun.
"""
import argparse
import json
from pathlib import Path
import sys

# Support the Docker entry point and package invocation with the same imports.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
from scripts.customer_report_data import APP, import_results, prepare_report
from scripts.customer_report_layout import CASE_WIDTHS, TRACE_WIDTHS, row_height
from scripts.customer_report_output import ReportOutputError, publish_workbook


def cell_rows(data):
    """Select the fifteen user-facing business fields, excluding automation metadata."""
    keys = ['id', 'title', 'module', 'description', 'preconditions', 'steps', 'input',
            'expected', 'actual', 'severity', 'priority', 'reproducibility',
            'evidence', 'reporter', 'status']
    return [[row[key] for key in keys] for row in data['cases']]


def write_workbook(data, target, media):
    """Create compact tables and keep analysis-to-case relations many-to-many."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.drawing.image import Image

    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets = [workbook.create_sheet(name) for name in data['sheet_names']]
    for sheet, title in zip(sheets, data['titles']):
        sheet.sheet_view.showGridLines = False
        sheet['A2'] = title
        sheet['A2'].font = Font(name='Arial', size=15, bold=True, color='17384A')
        sheet.row_dimensions[2].height = 25

    def table(sheet, row, headers, values, widths):
        """Write wrapped prose sized to its content, with filterable headers."""
        for col, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(col)].width = width
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row, col, header)
            cell.fill = PatternFill('solid', fgColor='19566B')
            cell.font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
            cell.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        sheet.row_dimensions[row].height = 42
        for index, record in enumerate(values, row + 1):
            sheet.row_dimensions[index].height = row_height(record, widths)
            for col, value in enumerate(record, 1):
                cell = sheet.cell(index, col, value)
                cell.font = Font(name='Arial', size=11, color='183442')
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                if index % 2:
                    cell.fill = PatternFill('solid', fgColor='EFF6F8')

    first, bva, ep, decision, guide, trace = sheets
    table(first, 6, data['headers'], cell_rows(data), CASE_WIDTHS)
    import os
    for index, record in enumerate(data['cases'], 7):
        paths = record['evidence'].splitlines()
        if paths:
            cell = first.cell(index, 13)
            cell.hyperlink = Path(os.path.relpath(APP / paths[0], Path(target).parent)).as_posix()
            cell.font = Font(name='Arial', size=11, color='0563C1', underline='single')
    first.freeze_panes = 'C7'
    first.auto_filter.ref = 'A6:O' + str(data['case_count'] + 6)
    choices = DataValidation(type='list', formula1='"' + ','.join(data['status_choices']) + '"')
    first.add_data_validation(choices)
    choices.add('O7:O' + str(data['case_count'] + 6))
    for row, (label, key) in enumerate(zip(data['bva_input_labels'], ('min', 'max', 'step', 'nominal')), 7):
        bva.cell(row, 1, label)
        bva.cell(row, 2, data['bva'][key]).fill = PatternFill('solid', fgColor='FFF1C6')
    formulas = ['=$B$7-$B$9', '=$B$7', '=$B$7+$B$9', '=$B$8-$B$9',
                '=$B$8', '=$B$8+$B$9', '=$B$10']
    values = [[item[0], item[1], formula, '', item[3]] for item, formula in zip(data['bva_rows'], formulas)]
    table(bva, 14, data['bva_headers'], values, [20, 34, 13, 20, 23])
    for row in range(15, 22):
        bva.cell(row, 4, '=IF(AND(C' + str(row) + '>=$B$7,C' + str(row) + '<=$B$8),"' + data['valid_partition'] + '","' + data['invalid_partition'] + '")')
    if data.get('extra_bva'):
        table(bva, 25, data['extra_bva_headers'], data['extra_bva'], [20, 34, 18, 55, 24])
    table(ep, 6, data['ep_headers'], data['ep'], [20, 22, 28, 35, 35, 20, 35])
    ep.auto_filter.ref = 'A6:G' + str(len(data['ep']) + 6)
    ep.freeze_panes = 'B7'
    for row, (label, value) in enumerate(zip(data['money_input_labels'], data['money_inputs']), 6):
        decision.cell(row, 9, label)
        decision.cell(row, 10, value).fill = PatternFill('solid', fgColor='FFF1C6')
    decision['J7'].number_format = '0%'
    position = 6
    for item in data['decisions']:
        decision.cell(position, 1, item['title'])
        position += 1
        records = []
        for group, rows in ((data['condition_label'], item['conditions']),
                            (data['action_label'], item['actions'])):
            records.extend([[group] + row for row in rows])
        widths = [14, 42] + [24] * len(item['rules'])
        table(decision, position, data['decision_headers'] + item['rules'], records, widths)
        first_condition = position + 1
        first_action = first_condition + len(item['conditions'])
        for first_row, length in ((first_condition, len(item['conditions'])),
                                  (first_action, len(item['actions']))):
            if length > 1:
                decision.merge_cells(start_row=first_row, start_column=1,
                                     end_row=first_row + length - 1, end_column=1)
        position += len(records) + 1
        if 'totals' in item:
            decision.cell(position, 2, data['shipping_total_label'] if item['rules'][0] == 'QD-VC-01' else data['total_label'])
            for index in range(len(item['rules'])):
                formula = '=$J$6'
                if item['rules'][0] == 'QD-KM-01' and index == 2:
                    formula = '=ROUND($J$6*(1-$J$7),2)'
                if item['rules'][0] == 'QD-VC-01':
                    formula = '=ROUND($J$6*(1-$J$7)+$J$' + str(index + 8) + ',2)'
                decision.cell(position, index + 3, formula).number_format = '0.00'
            decision.row_dimensions[position].height = 32
            position += 1
        decision.cell(position, 2, data['related_cases_label'])
        for index, identifiers in enumerate(item['case_ids'], 3):
            cell = decision.cell(position, index, identifiers)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            cell.font = Font(name='Arial', size=11, color='183442')
        decision.row_dimensions[position].height = 59
        position += 4
    table(guide, 6, data['guide_headers'], data['guide'], [28, 88])
    table(trace, 6, data['trace_headers'], data['trace'], TRACE_WIDTHS)
    trace.freeze_panes = 'B7'
    trace.auto_filter.ref = 'A6:F' + str(data['case_count'] + 6)
    image_row = {'BVA': 29 + len(data.get('extra_bva', [])), 'EP': len(data['ep']) + 10, 'Decision': position + 2}
    by_kind = {'BVA': bva, 'EP': ep, 'Decision': decision}
    for item in media:
        image = Image(item['png'])
        image.height = round(image.height * 850 / image.width)
        image.width = 850
        by_kind[item['sheet']].add_image(image, 'A' + str(image_row[item['sheet']]))
        image_row[item['sheet']] += max(29, int(image.height / 20) + 3)
    workbook.save(target)


def main():
    """Always export Excel; import old runs only as separate trace references."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media', action='store_true', help='Embed and export PNG/SVG design figures.')
    parser.add_argument('--results', type=Path, help='Existing Robot XML or sanitized JSON, relative to the app.')
    options = parser.parse_args()
    output = APP / 'reports/customer'
    output.mkdir(parents=True, exist_ok=True)
    results = None
    evidence = ''
    selected = options.results
    if selected is None and (APP / 'reports/output.xml').is_file():
        selected = Path('reports/output.xml')
    if selected:
        source = (APP / selected).resolve()
        if selected.is_absolute() or APP not in source.parents:
            parser.error('--results must be an existing app-relative file.')
        results = import_results(source)
        results['source_selected_path'] = source.relative_to(APP).as_posix()
        destination = output / 'evidence' / ('run-' + results['source_sha256'][:12]) / 'results.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        results['source_path'] = destination.relative_to(APP).as_posix()
        destination.write_text(json.dumps(results, indent=2) + '\n')
        evidence = destination.relative_to(APP).as_posix()
    data = prepare_report(results=results, evidence_path=evidence)
    media = []
    if options.media:
        from scripts.customer_report_media import create_media
        media = create_media(data, output / 'media')
    (output / 'report_data.json').write_text(json.dumps(data['_english_report'], indent=2) + '\n', encoding='utf-8')
    saved, warnings = publish_workbook(output / 'customer_test_cases.xlsx',
                                       lambda target: write_workbook(data, target, media))
    for warning in warnings:
        print('WARNING:', warning)
    print('Excel report:', saved)
    print('Business cases:', data['case_count'], '; related Robot executions:', data['automation_count'], '; imported evidence does not set new outcomes.')
    print('Verified UI screenshots:', data['screenshot_count'])
    for warning in data['evidence_warnings']:
        print('WARNING:', warning)
    print('Media files:', len(media) * 2)


if __name__ == '__main__':
    try:
        main()
    except ReportOutputError as error:
        print('ERROR:', error, file=sys.stderr)
        raise SystemExit(2)
    except OSError as error:
        print('ERROR: Customer report files could not be read or written. Check the selected input, report-folder permissions and free disk space. Details: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
