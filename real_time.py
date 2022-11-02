import matplotlib.pyplot as plt
import numpy as np
from mne.io import RawArray

import pygds
from classifiers.flat import process
from config import configurations, experiment_frequency_range




def get_individual_accuracy(predicions, correct):
    all = [0, 0, 0]
    cor = [0, 0, 0]
    for i in range(len(predicions)):
        all[correct[i]] += 1
        if predicions[i] == correct[i]:
            cor[predicions[i]] += 1
    results = [2, 2, 2]
    if all[0] > 0: results[0] = cor[0] / all[0]
    if all[1] > 0: results[1] = cor[1] / all[1]
    if all[2] > 0: results[2] = cor[2] / all[2]
    return results


def create_confusion_matrix(n_classes, predictions_sets, corrects_sets):
    confusion_matrix = np.zeros((n_classes, n_classes))
    for fold_index in range(len(predictions_sets)):
        predictions = predictions_sets[fold_index]
        corrects = corrects_sets[fold_index]
        for index in range(len(predictions)):
            confusion_matrix[predictions[index]][corrects[index]] += 1
    return confusion_matrix


def calculate_recall(predictions, corrects, hand):
    numerator = 0
    denominator = 0
    for i in range(len(predictions)):
        if hand == corrects[i]:  # Actual condition: Positive
            if predictions[i] == corrects[i]:  # Predicted condition: Positive
                numerator += 1  # TP
            denominator += 1  # TP + FN
    if denominator == 0: return 0, 0
    return numerator, denominator


def calculate_precision(predictions, corrects, hand):
    numerator = 0
    denominator = 0
    for i in range(len(predictions)):
        if hand == predictions[i]:  # Predicted condition: Positive
            if predictions[i] == corrects[i]:  # Actual condition: Positive
                numerator += 1  # TP
            denominator += 1  # TP + FP
    if denominator == 0: return 0, 0
    return numerator, denominator


def calculate_combined_recall(predictions, corrects):
    recall_data = []
    for i in range(3):
        recall_data.append(calculate_recall(predictions, corrects, i))
    numerator = 0
    denominator = 0
    for i in recall_data:
        numerator += i[0]
        denominator += i[1]
    if denominator == 0: return 0
    return numerator / denominator


def calculate_combined_precision(predictions, corrects):
    recall_data = []
    for i in range(3):
        recall_data.append(calculate_precision(predictions, corrects, i))
    numerator = 0
    denominator = 0
    for i in recall_data:
        numerator += i[0]
        denominator += i[1]
    if denominator == 0: return 0
    return numerator / denominator


def main(subjects_id, bands, channels, randomness):

    precision_numerator = [0, 0]
    precision_denominator = [0, 0]
    recall_numerator = [0, 0]
    recall_denominator = [0, 0]

    window_times, window_scores, csp_filters, epochs_info, predictions, corrects, classifier, mne_info = process(bands, channels,
                                                                                           randomness, n_splits=1)

    # update_predictions = []
    # for i in range(len(predictions)):
    #     update_predictions.append([])
    #     for j in range(len(predictions[i])):
    #         if predictions[i][j] == 0:
    #             update_predictions[i].append(1)
    #         else:
    #             update_predictions[i].append(0)
    # predictions = update_predictions

    for i in range(len(predictions)):
        for j in range(2):
            nprec, dprec = calculate_precision(predictions[i], corrects[i], j)
            nrec, drec = calculate_recall(predictions[i], corrects[i], j)
            precision_numerator[j] = precision_numerator[j] + nprec
            precision_denominator[j] = precision_denominator[j] + dprec
            recall_numerator[j] = recall_numerator[j] + nrec
            recall_denominator[j] = recall_denominator[j] + drec

    accuracy_nominator = 0
    accuracy_denumerator = 0
    for i in range(len(predictions)):
        for j in range(len(predictions[i])):
            accuracy_denumerator += 1
            if predictions[i][j] == corrects[i][j]:
                accuracy_nominator += 1

    print('Accuracy: {}'.format(accuracy_nominator / accuracy_denumerator))

    final_precision = [0, 0]
    final_recall = [0, 0]
    for i in range(2):
        if precision_denominator[i] == 0:
            final_precision[i] = 0
        else:
            final_precision[i] = precision_numerator[i] / precision_denominator[i]

    for i in range(2):
        if recall_denominator[i] == 0:
            final_recall[i] = 0
        else:
            final_recall[i] = recall_numerator[i] / recall_denominator[i]

    print('Combined precision for movement class: {}'.format(final_precision[0]))
    print('Combined precision for rest class: {}'.format(final_precision[1]))

    print('Combined recall for movement class: {}'.format(final_recall[0]))
    print('Combined recall for rest class: {}'.format(final_recall[1]))

    return csp_filters, classifier, mne_info


def configuration_to_label(config):
    channels = config['channels']
    if len(channels) == 0:
        channels = 'all'
    else:
        channels = len(channels)
    return '{}Hz width {} channels {} randomness'.format(
        config['band_width'],
        channels,
        config['randomness'])



# print(main(
#             [1],
#             [(10,15), (19,22)],
#             [],
#             0
#         ))
band0 = 10
band1 = 14
csp, lda, mne_info = main(
            [1],
            [(band0, band1)],
            configurations[0]['channels'],
            configurations[0]['randomness']
        )
print(csp, lda)

print("Inicjalizacja trochę trwa...")
d = pygds.GDS()
pygds.configure_demo(d) # Tu sie trzeba przyjrzec blizej - co i jak tam jest ustawiane
d.SetConfiguration()
i = 0
def processCallback(samples):
    # samples = raw_samples[:,0:32]
    global i
    i+=1
    try:
        ret = []
        for _ in range(32):
            ret.append([])
        for sample in samples:
            for index, channel in enumerate(sample):
                if index < 32:
                    ret[index].append(channel)
        raw = RawArray(ret,mne_info, verbose='CRITICAL')
        raw.filter(band0, band1, l_trans_bandwidth=2, h_trans_bandwidth=2, filter_length=500, fir_design='firwin',
                                      skip_by_annotation='edge', verbose='CRITICAL')
        flt = raw.get_data()
        res = lda.predict(csp.transform(np.array([flt])))
        if res[0] == 0:
            print('Movement')
        else: print('Rest')
    except Exception as e:
        print(e)




    if i < 10:return True
    return False

a = d.GetData(d.SamplingRate*2, processCallback)
# labels = list(map(configuration_to_label, configurations))
# processed_data = []
# for i in range(len(configurations)):
#     processed_data.append([])
# bins = []
# for frequency in range(experiment_frequency_range[0], experiment_frequency_range[1]):
#     for index, configuration in enumerate(configurations):
#         processed_data[index].append(main(
#             [1],
#             [(frequency, frequency + configuration['band_width'])],
#             configuration['channels'],
#             configuration['randomness']
#         ))
#     bins.append('{}Hz'.format(frequency))
#
# for index, label in enumerate(labels):
#     plt.plot(bins, processed_data[index], label=label)
# plt.legend()
# plt.show()