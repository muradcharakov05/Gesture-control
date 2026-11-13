"""One source of truth for the preview rectangle and cursor coordinate mapping."""
def working_area(config, margin=None):
    if config.get('area_mode') == 'calibrated' and config.get('bounds'):
        return tuple(config['bounds'])
    margin = config.get('margin', .15) if margin is None else margin
    margin = max(.05, min(.3, float(margin)))
    return margin, margin, 1-margin, 1-margin
