import { createSlice } from "@reduxjs/toolkit";

const gptSlice = createSlice({
  name: "gpt",
  initialState: {
    showGptSearch: false,
    gptSearchedMovies: null,
    movieName:null
  },
  reducers: {
    toggleGptSearchView: (state) => {
      state.showGptSearch = !state.showGptSearch;
    },
    addGptMovieResult: (state, action) => {
      const {movieName , gptSearchedMovies} = action.payload
      state.movieName = movieName
      state.gptSearchedMovies =gptSearchedMovies
    },
  },
});

export const { toggleGptSearchView ,addGptMovieResult} = gptSlice.actions;

export default gptSlice.reducer;
