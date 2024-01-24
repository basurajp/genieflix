import { createSlice } from "@reduxjs/toolkit";

const movieSlice = createSlice({
  name: "movies",
  initialState: {
    nowPlayingMovies: null,
    movieTrailer: null,
    popularMovies: null,
    topratedMovies: null,
    upComingMvies: null,
  },
  reducers: {
    addNowPlayingMovies: (state, action) => {
      state.nowPlayingMovies = action.payload;
    },
    addMovietrailer: (state, action) => {
      state.movieTrailer = action.payload;
    },
    addPoularMovies: (state, action) => {
      state.popularMovies = action.payload;
    },
    addtopratedMovies: (state, action) => {
      state.topratedMovies = action.payload;
    },
    addupComingMovies: (state, action) => {
      state.upComingMvies = action.payload;
    },
  },
});

export const {
  addNowPlayingMovies,
  addMovietrailer,
  addPoularMovies,
  addtopratedMovies,
  addupComingMovies,
} = movieSlice.actions;

export default movieSlice.reducer;
