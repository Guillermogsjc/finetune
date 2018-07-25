from finetune.base import BaseModel
from finetune.encoding import EncodedOutput, ArrayEncodedOutput
from finetune.target_encoders import SequenceLabelingEncoder
from finetune.network_modules import sequence_labeler
from finetune.utils import indico_to_finetune_sequence, finetune_to_indico_sequence
from sklearn.model_selection import train_test_split


class SequenceLabeler(BaseModel):

<<<<<<< HEAD
    def _text_to_ids_with_labels(self, X, Y=None):
        # X: list of list of text snippets.  Each snippet represents a segment of text with a consistent label
        encoder_out = self.encoder.encode_sequence_labeling(X, Y=Y, max_length=self.config.max_length)
        return self._array_format(encoder_out)

    def _finetune(self, X, Y, batch_size=None):
        """
        X: List / array of text
        Y: Class labels
        val_size: Float fraction or int number that represents the size of the validation set.
        val_interval: The interval for which validation is performed, measured in number of steps.
        """
        self.label_encoder = self._get_target_encoder()
        train_x, test_x, train_y, test_y = train_test_split(X, Y, test_size=self.config.val_size,
                                                            random_state=self.config.seed)

        array_encoded_train = self._text_to_ids_with_labels(train_x, Y=train_y)
        array_encoded_val = self._text_to_ids_with_labels(test_x, Y=test_y)

        train_y = self.label_encoder.fit_transform(array_encoded_train.labels)
        test_y = self.label_encoder.transform(array_encoded_val.labels)

        return self._training_loop(arr_encoded_train=array_encoded_train, train_y=train_y,
                                   arr_encoded_val=array_encoded_val, val_y=test_y, batch_size=batch_size)

    def _get_target_encoder(self):
        return SequenceLabelingEncoder()

=======
>>>>>>> c1e6ea5... WIP: refactor target_type logic and subclasses
    def finetune(self, X, Y, batch_size=None):
        """
        :param X: A list of text snippets. Format: [batch_size]
        :param Y: A list of lists of annotations. Format: [batch_size, n_annotations], where each annotation is of the form:
            {'start': char_idx, 'end': char_idx, 'label': 'label'}
        :param batch_size: integer number of examples per batch. When N_GPUS > 1, this number
                           corresponds to the number of training examples provided to each GPU.
        :param val_size: Float fraction or int number that represents the size of the validation set.
        :param val_interval: The interval for which validation is performed, measured in number of steps.
        """
        X, Y = indico_to_finetune_sequence(X, Y, none_value="<PAD>")
        arr_encoded = self._text_to_ids(X, Y=Y)
        return self._training_loop(
            arr_encoded,
            Y=arr_encoded.labels,
            batch_size=batch_size or self.config.batch_size
        )

    def predict(self, X, max_length=None):
        """
        Produces a list of most likely class labels as determined by the fine-tuned model.

        :param X: A list / array of text, shape [batch]
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncatindiion.
        :returns: list of class labels.
        """
        doc_subseqs, _ = indico_to_finetune_sequence(X)
        arr_encoded = self._text_to_ids(doc_subseqs)
        labels = self._predict(X, max_length=max_length)
        all_subseqs = []
        all_labels = []
        for text, label_seq, position_seq in zip(X, labels, arr_encoded.char_locs):
            start_of_token = 0
            doc_subseqs = []
            doc_labels = []

            for label, position in zip(label_seq, position_seq):
                if position == -1:
                    # indicates padding / special tokens
                    continue

                # if there are no current subsequence
                # or the current subsequence has the wrong label
                if not doc_subseqs or label != doc_labels[-1]:
                    # start new subsequence
                    doc_subseqs.append(text[start_of_token:position])
                    doc_labels.append(label)
                else:
                    # continue appending to current subsequence
                    doc_subseqs[-1] += text[start_of_token:position]

                start_of_token = position
            all_subseqs.append(doc_subseqs)
            all_labels.append(doc_labels)
        doc_texts, doc_annotations = finetune_to_indico_sequence(raw_texts=X, subseqs=all_subseqs, labels=all_labels)
        return doc_annotations

    def featurize(self, Xs, max_length=None):
        """
        Embeds inputs in learned feature space. Can be called before or after calling :meth:`finetune`.

        :param Xs: An iterable of lists or array of text, shape [batch, n_inputs, tokens]
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncation.
        :returns: np.array of features of shape (n_examples, embedding_size).
        """
        return self._featurize(*list(zip(*Xs)), max_length=max_length)

    def predict_proba(self, X, max_length=None):
        """
        Produces a list of most likely class labels as determined by the fine-tuned model.

        :param X: A list / array of text, shape [batch]
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncatindiion.
        :returns: list of class labels.
        """
        doc_subseqs, _ = indico_to_finetune_sequence(X)
        arr_encoded = self._text_to_ids(doc_subseqs)
        batch_probas = self._predict_proba(X, max_length=max_length)
        result = []
        for token_seq, proba_seq in zip(arr_encoded.tokens, batch_probas):
            result.append(list(zip(token_seq, proba_seq)))
        return result

    def _target_placeholder(self):
        return tf.placeholder(tf.int32, [None, self.config.max_length])  # classification targets

    def _target_encoder(self):
        return SequenceLabelingEncoder()

    def _target_model(self, featurizer_state, targets, n_outputs, train=False, reuse=None, **kwargs):
        return sequence_labeler(
            hidden=featurizer_state['sequence_features'],
            targets=targets, 
            n_targets=n_outputs,
            dropout_placeholder=self.do_dropout,
            config=self.config,
            train=train, 
            reuse=reuse, 
            **kwargs
        )
    
    def _predict_op(self, logits, **kwargs):
        label_idxs, _ = sequence_decode(logits, kwargs.get("transition_matrix"))
        return label_idxs

    def _predict_proba_op(self, logits, **kwargs):
        _, label_probas = sequence_decode(logits, kwargs.get("transition_matrix"))
        return label_probas
