# example of a dcgan on cifar10
import os
import numpy as np
from numpy import zeros
from numpy import ones
from numpy.random import randn
from numpy.random import randint
import tensorflow
from tensorflow.keras.datasets.cifar10 import load_data
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Reshape, Flatten, Conv2D, Conv2DTranspose, LeakyReLU, Dropout
from matplotlib import pyplot

# define the standalone discriminator model
def define_discriminator(in_shape=(32, 32, 3)):
    model = Sequential([
        Conv2D(64,(3,3),padding='same',input_shape=in_shape),
        LeakyReLU(alpha=0.2),
        Conv2D(128,(3,3),strides=(2,2),padding='same'),
        LeakyReLU(alpha=0.2),
        Conv2D(128,(3,3),strides=(2,2),padding='same'),
        LeakyReLU(alpha=0.2),
        Conv2D(256,(3,3),strides=(2,2),padding='same'),
        LeakyReLU(alpha=0.2),
        Flatten(),
        Dropout(0.4),
        Dense(1,activation='sigmoid'),

    ])
    model.compile(
        loss='binary_crossentropy', 
        optimizer=Adam(lr=0.0002, beta_1=0.5), 
        metrics=['accuracy'])
    return model

# define the standalone generator model
def define_generator(latent_dim):
    n_nodes = 256 * 4 * 4
    model = Sequential([
        Dense(n_nodes, input_dim=latent_dim),
        LeakyReLU(alpha=0.2),
        Reshape((4,4,256)),
        Conv2DTranspose(128,4,strides=2,padding='same'),
        LeakyReLU(alpha=0.2),
        Conv2DTranspose(128,4,strides=2,padding='same'),
        LeakyReLU(alpha=0.2),
        Conv2DTranspose(128,4,strides=2,padding='same'),
        LeakyReLU(alpha=0.2),
        Conv2D(3,3,activation='tanh',padding='same')
    ])
    return model

# define the combined generator and discriminator model, for updating the generator
def define_gan(g_model, d_model):
    d_model.trainable = False
    model = Sequential([
        g_model,
        d_model
    ])
    model.compile(
        loss='binary_crossentropy',
        optimizer=Adam(lr=0.0002, beta_1=0.5))
    return model

# load and prepare cifar10 training images
def load_real_samples():
    (trainX, trainY), (_, _) = load_data()
    # filter for specific label in dataset
    newArr = []
    i = 0
    while i < len(trainX):
        # filter for label boats (8)
        if trainY[i][0] == 8:
            newArr.append(trainX[i])
            
        i += 1
    trainX = np.array(newArr)
    X = trainX.astype('float32')
    X = (X - 127.5) / 127.5
    return X

# select real samples
def generate_real_samples(dataset, n_samples):
    # choose random instances
    ix = randint(0, dataset.shape[0], n_samples)
    # retrieve selected images
    X = dataset[ix]
    # generate 'real' class labels (1)
    y = ones((n_samples, 1))
    return X, y

# generate points in latent space as input for the generator
def generate_latent_points(latent_dim, n_samples):
    # generate points in the latent space
    x_input = randn(latent_dim * n_samples)
    # reshape into a batch of inputs for the network
    x_input = x_input.reshape(n_samples, latent_dim)
    return x_input

# use the generator to generate n fake examples, with class labels
def generate_fake_samples(g_model, latent_dim, n_samples):
    # generate points in latent space
    x_input = generate_latent_points(latent_dim, n_samples)
    # predict outputs
    X = g_model.predict(x_input)
    # create 'fake' class labels (0)
    y = zeros((n_samples, 1))
    return X, y

# create and save a plot of generated images
def save_plot(examples, epoch, n=7):
    # scale from [-1,1] to [0,1]
    examples = (examples + 1) / 2.0
    # plot images
    for i in range(n * n):
        # define subplot
        pyplot.subplot(n, n, 1 + i)
        # turn off axis
        pyplot.axis('off')
        # plot raw pixel data
        pyplot.imshow(examples[i])
    # save plot to file
    filename = path_ex + '/generated_plot_e%03d.png' % (epoch+1)
    pyplot.savefig(filename)
    pyplot.close()

# evaluate the discriminator, plot generated images, save generator model
def summarize_performance(epoch, g_model, d_model, dataset, latent_dim, n_samples=150):
    # prepare real samples
    X_real, y_real = generate_real_samples(dataset, n_samples)
    # evaluate discriminator on real examples
    _, acc_real = d_model.evaluate(X_real, y_real, verbose=0)
    # prepare fake examples
    x_fake, y_fake = generate_fake_samples(g_model, latent_dim, n_samples)
    # evaluate discriminator on fake examples
    _, acc_fake = d_model.evaluate(x_fake, y_fake, verbose=0)
    # summarize discriminator performance and save to file
    print('>Accuracy real: %.0f%%, fake: %.0f%%' %
          (acc_real*100, acc_fake*100))
    with open("summary.txt", "a") as myfile:
        myfile.write(str(acc_real) + "," + str(acc_fake) + ";")
    # save plot
    save_plot(x_fake, epoch)
    # save the generator model tile file
    filename = '/model_%03d.h5' % (epoch+1)
    g_model.save(filename)

# train gan
def train(g_model, d_model, gan_model, dataset, latent_dim, n_epochs=200, n_batch=128):
    bat_per_epo = int(dataset.shape[0] / n_batch)
    half_batch = int(n_batch / 2)
    for i in range(n_epochs):
        for j in range(bat_per_epo):
            X_real, y_real = generate_real_samples(dataset, half_batch)
            X_fake, y_fake = generate_fake_samples(g_model, latent_dim, half_batch)
            # update discriminator model weights on real samples
            d_loss1, _ = d_model.train_on_batch(X_real, y_real)
            # update discriminator model weights on fake samples
            d_loss2, _ = d_model.train_on_batch(X_fake, y_fake)
            # prepare points in latent space as input for the generator
            X_gan = generate_latent_points(latent_dim, n_batch)
            # create inverted labels for the fake samples
            y_gan = ones((n_batch, 1))
            # update the generator via the discriminator's error
            g_loss = gan_model.train_on_batch(X_gan, y_gan)
            # summarize loss on this batch
            print('>%d, %d/%d, d1=%.3f, d2=%.3f g=%.3f' %(i+1, j+1, bat_per_epo, d_loss1, d_loss2, g_loss))
        # evaluate the model performance, sometimes
        print("Epoch: " + i+1)
        if (i+1) % 1 == 0:
            summarize_performance(i, g_model, d_model, dataset, latent_dim)


# size of the latent space
latent_dim = 100
# create the discriminator
d_model = define_discriminator()
# create the generator
g_model = define_generator(latent_dim)
# create the gan
gan_model = define_gan(g_model, d_model)
# load image data
dataset = load_real_samples()
# train model
train(g_model, d_model, gan_model, dataset, latent_dim, 2000)
