"""One source of truth for the preview rectangle and cursor coordinate mapping."""
def working_area(config, margin=None):
    bottom = 1.0 - max(0., min(.4, float(config.get('bottom_margin', .2))))
    if config.get('area_mode') == 'calibrated' and config.get('bounds'):
        left, top, right, _ = config['bounds']
        return left, min(top, bottom-.1), right, bottom
    margin = config.get('margin', .15) if margin is None else margin
    margin = max(.05, min(.3, float(margin)))
    return margin, margin, 1-margin, bottom
