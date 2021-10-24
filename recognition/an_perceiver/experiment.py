import argparse
import os
import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow.keras import callbacks, losses, metrics
from tensorflow_addons import optimizers

import aoi_akoa  # register dataset
from perceiver import Perceiver
from preprocessing import preprocess


def run_experiment(opts):
    """Run perceiver classification experiment on aoi_akoa dataset."""

    splits, info = tfds.load(
        "aoi_akoa",
        split=["train", "validation", "test"],
        data_dir=opts.data_dir,
        with_info=True,
        as_supervised=True,
    )

    num_classes = info.features["label"].num_classes
    train, validation, test = preprocess(
        *splits,
        batch_size=opts.batch_size,
        num_classes=num_classes,
        image_dims=opts.image_dims
    )

    perceiver = Perceiver(
        num_blocks=opts.num_blocks,
        num_self_attends_per_block=opts.num_self_attends_per_block,
        num_cross_heads=opts.num_cross_heads,
        num_self_attend_heads=opts.num_self_attend_heads,
        latent_dim=opts.latent_dim,
        latent_channels=opts.latent_channels,
        num_freq_bands=opts.num_freq_bands,
        num_classes=num_classes,
    )

    perceiver.compile(
        optimizer=optimizers.LAMB(
            learning_rate=opts.learning_rate,
            weight_decay_rate=opts.weight_decay_rate,
        ),
        loss=losses.CategoricalCrossentropy(from_logits=True),
        metrics=[metrics.CategoricalAccuracy(name="accuracy")],
    )

    csv_logger = callbacks.CSVLogger(filename=os.path.join(opts.out_dir, "history.csv"))
    model_checkpointer = callbacks.ModelCheckpoint(
        filepath=os.path.join(opts.out_dir, "checkpoint"), save_weights_only=True
    )

    history = perceiver.fit(
        x=train,
        epochs=opts.epochs,
        validation_data=validation,
        callbacks=[model_checkpointer, csv_logger],
    )

    perceiver.save(os.path.join(opts.out_dir, "perceiver"), save_format="h5")
    loss, accuracy = perceiver.evaluate(test)

    eval_result = {"loss": loss, "accuracy": accuracy}
    with open(os.path.join(opts.out_dir, "eval.txt"), "w") as file:
        print(eval_result, file=file)

    print("\n", "evaluation:", eval_result)


def get_opts():
    """Parses command line options."""

    parser = argparse.ArgumentParser(
        description="Perceiver classification experiement for AOI AKOA knee laterality.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # other
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        help="tensorflow log level",
    )

    parser.add_argument(
        "--show-config",
        action="store_true",
        default=True,
        help="show experiement config",
    )

    # training options
    training = parser.add_argument_group("training options")
    training.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="number of training epochs",
    )
    training.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="batch size for all splits, in training and evaluation",
    )
    training.add_argument(
        "--out-dir",
        type=str,
        default="./training",
        help="dir for training outputs",
    )

    # dataset options
    dataset = parser.add_argument_group("dataset options")
    dataset.add_argument(
        "--data-dir",
        type=str,
        default="~/tensorflow_datasets",
        help="location of tensorflow datasets data",
    )
    dataset.add_argument(
        "--image-dims",
        type=int,
        nargs="+",
        help="resize images without distortion",
    )

    # perceiver options
    perceiver = parser.add_argument_group("perceiver options")
    perceiver.add_argument(
        "--num-blocks",
        type=int,
        default=8,
        help="number of blocks",
    )
    perceiver.add_argument(
        "--num-self-attends-per-block",
        type=int,
        default=6,
        help="number of self attention layers per block",
    )
    perceiver.add_argument(
        "--num-cross-heads",
        type=int,
        default=1,
        help="number of cross attention heads",
    )
    perceiver.add_argument(
        "--num-self-attend-heads",
        type=int,
        default=8,
        help="number of self attention heads",
    )
    perceiver.add_argument(
        "--latent-dim",
        type=int,
        default=512,
        help="latent array dimension",
    )
    perceiver.add_argument(
        "--latent-channels",
        type=int,
        default=1024,
        help="latent array channels",
    )
    perceiver.add_argument(
        "--num-freq-bands",
        type=int,
        default=64,
        help="frequency bands for fourier position encoding",
    )

    # optimiser options
    optimiser = parser.add_argument_group("optimiser options")
    optimiser.add_argument(
        "--learning-rate",
        type=float,
        default=4e-3,
        help="learning rate",
    )
    optimiser.add_argument(
        "--weight-decay-rate",
        type=float,
        default=1e-1,
        help="weight decay rate",
    )

    args = parser.parse_args()
    assert args.image_dims is None or len(args.image_dims) == 2
    if args.image_dims is not None:
        args.image_dims = tuple(args.image_dims)

    return args


def main():
    opts = get_opts()
    tf.get_logger().setLevel(opts.log_level)

    if opts.show_config:
        print("experiment config:")
        for arg in vars(opts):
            print(f"  {arg}:", getattr(opts, arg))

    run_experiment(opts)


if __name__ == "__main__":
    main()