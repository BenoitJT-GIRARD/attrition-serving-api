"""From the three raw extracts to the feature frame the model consumes.

`io` reads and anonymises, `cleaning` decides what a missing value means, `features`
derives the ratios the model uses. Nothing here knows about a model or a threshold.
"""
